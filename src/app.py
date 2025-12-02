import os
import time
import logging
import json
from decimal import Decimal

from flask import Flask, request, jsonify, send_from_directory
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, text
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base, relationship
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

# ---------------------------
# OpenTelemetry / SigNoz
# ---------------------------
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# ---------------------------
# CONFIGURAÇÃO APP
# ---------------------------
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://meuuser:supersegredo@db:5432/minhadb"
SIGNOZ_KEY = os.getenv("SIGNOZ_KEY2")
SIGNOZ_HTTP_ENDPOINT = "https://ingest.us.signoz.cloud:443/v1/traces"

app = Flask(__name__, static_folder="static", static_url_path="/static")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

# ---------------------------
# LOGS ESTRUTURADOS
# ---------------------------
logger = logging.getLogger("supermercado")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    json.dumps({
        "time": "%(asctime)s",
        "level": "%(levelname)s",
        "message": "%(message)s"
    })
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# ---------------------------
# MODELS
# ---------------------------
class Categoria(Base):
    __tablename__ = "categorias"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), unique=True, nullable=False)
    produtos = relationship("Produto", back_populates="categoria")

class Produto(Base):
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    preco = Column(Numeric(10, 2), nullable=False)
    estoque = Column(Integer, default=0)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    categoria = relationship("Categoria", back_populates="produtos")

def produto_to_dict(p: Produto):
    return {
        "id": p.id,
        "nome": p.nome,
        "preco": float(p.preco),
        "estoque": p.estoque,
        "categoria": p.categoria.nome if p.categoria else None,
    }

# ---------------------------
# DB WAIT
# ---------------------------
def wait_for_db(retries=20):
    for _ in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Banco disponível")
            return True
        except Exception:
            logger.info("DB não pronto, tentando novamente...")
            time.sleep(2)
    raise RuntimeError("Banco de dados não disponível após várias tentativas")

# ---------------------------
# OPENTELEMETRY HTTP
# ---------------------------
trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: "supermercado-app"}))
)
tracer = trace.get_tracer(__name__)

otlp_exporter = OTLPSpanExporter(
    endpoint=SIGNOZ_HTTP_ENDPOINT,
    headers={"authorization": f"Bearer {SIGNOZ_KEY}"}
)

span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

FlaskInstrumentor().instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)

# ---------------------------
# PROMETHEUS
# ---------------------------
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/metrics": make_wsgi_app()
})

# ---------------------------
# ROTAS
# ---------------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

@app.route("/produtos", methods=["GET"])
def get_produtos():
    session = SessionLocal()
    produtos = session.query(Produto).all()
    session.close()
    logger.info("Listando produtos")
    return jsonify([produto_to_dict(p) for p in produtos])

@app.route("/produtos", methods=["POST"])
def create_produto():
    session = SessionLocal()
    data = request.json
    p = Produto(
        nome=data["nome"],
        preco=Decimal(data["preco"]),
        estoque=data.get("estoque", 0),
        categoria_id=data.get("categoria_id")
    )
    session.add(p)
    session.commit()
    logger.info(f"Produto criado: {p.nome}")
    produto_id = p.id
    session.close()
    return jsonify({"message": "Produto criado", "id": produto_id})

@app.route("/produtos/<int:produto_id>", methods=["PUT"])
def update_produto(produto_id):
    session = SessionLocal()
    produto = session.query(Produto).get(produto_id)
    if not produto:
        session.close()
        return jsonify({"error": "Produto não encontrado"}), 404
    data = request.json
    produto.nome = data["nome"]
    produto.preco = Decimal(data["preco"])
    produto.estoque = data.get("estoque", produto.estoque)
    produto.categoria_id = data.get("categoria_id")
    session.commit()
    logger.info(f"Produto atualizado: {produto.nome}")
    session.close()
    return jsonify({"message": "Produto atualizado"})

@app.route("/produtos/<int:produto_id>", methods=["DELETE"])
def delete_produto(produto_id):
    session = SessionLocal()
    produto = session.query(Produto).get(produto_id)
    if not produto:
        session.close()
        return jsonify({"error": "Produto não encontrado"}), 404
    session.delete(produto)
    session.commit()
    logger.info(f"Produto deletado: {produto.nome}")
    session.close()
    return jsonify({"message": "Produto deletado"})

@app.route("/categorias", methods=["GET"])
def get_categorias():
    session = SessionLocal()
    categorias = session.query(Categoria).all()
    session.close()
    logger.info("Listando categorias")
    return jsonify([{"id": c.id, "nome": c.nome} for c in categorias])

# ---------------------------
# RUN
# ---------------------------
if __name__ == "__main__":
    wait_for_db()
    Base.metadata.create_all(engine)
    logger.info("Servidor iniciado com OTel + SigNoz (HTTP) + Prometheus")
    app.run(host="0.0.0.0", port=80)
