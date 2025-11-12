#!/usr/bin/env python3
import os
import time
import logging
import json
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignK                                                                                                             ey, text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relat                                                                                                             ionship

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExport                                                                                                             er
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware

PORT = int(os.getenv("PORT", 5000))
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://meuuser:supersegredo@d                                                                                                             b:5432/minhadb"

# Old-style Signoz vars (you requested these)
SIGNOZ_OTLP_URL = os.getenv("SIGNOZ_OTLP_URL")
SIGNOZ_INGEST_KEY = os.getenv("SIGNOZ_INGEST_KEY")

app = Flask(__name__, static_folder="static", static_url_path="/static")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

logger = logging.getLogger("supermercado")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(json.dumps({
    "time": "%(asctime)s",
    "level": "%(levelname)s",
    "message": "%(message)s"
}))
handler.setFormatter(formatter)
logger.addHandler(handler)

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
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    estoque = Column(Integer, default=0)
    categoria = relationship("Categoria", back_populates="produtos")

def produto_to_dict(p: Produto):
    return {
        "id": p.id,
        "nome": p.nome,
        "preco": float(p.preco),
        "estoque": p.estoque,
        "categoria": p.categoria.nome if p.categoria else None,
    }

def wait_for_db(retries=20):
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Banco disponível")
            return True
        except Exception:
            logger.info("DB não pronto, tentando novamente...")
            time.sleep(2)
    return False

service_name = os.getenv("SERVICE_NAME") or os.getenv("OTEL_SERVICE_NAME") or "s                                                                                                             upermercado-app"
trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
)
tracer = trace.get_tracer(__name__)

def normalize_signoz_endpoint(raw: str):
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        host = parsed.hostname
        port = parsed.port or 4317
        return f"{host}:{port}"
    return raw

endpoint = normalize_signoz_endpoint(SIGNOZ_OTLP_URL)

# Defensive checks
if not endpoint:
    logger.error("SIGNOZ_OTLP_URL não definido. Traces NÃO serão enviados.")
if not SIGNOZ_INGEST_KEY:
    logger.error("SIGNOZ_INGEST_KEY não definido. Traces serão rejeitados como U                                                                                                             NAUTHENTICATED pelo SigNoz.")

# Prepare multiple header variants to maximize compatibility
headers = [
    ("signoz-ingest-key", SIGNOZ_INGEST_KEY or ""),
    ("signoz-ingestion-key", SIGNOZ_INGEST_KEY or ""),
    ("x-signoz-ingest-key", SIGNOZ_INGEST_KEY or ""),
]

masked_key = (SIGNOZ_INGEST_KEY[:6] + "..." + SIGNOZ_INGEST_KEY[-4:]) if SIGNOZ_                                                                                                             INGEST_KEY else "<missing>"
logger.info(f"OTLP exporter endpoint={endpoint}, header_names={[h[0] for h in he                                                                                                             aders]}, ingest_key_masked={masked_key}")

try:
    otlp_exporter = OTLPSpanExporter(
        endpoint=endpoint or None,
        insecure=False,
        headers=tuple(headers),
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    logger.info("OTLPSpanExporter criado (enviando múltiplos headers para SigNoz                                                                                                             ).")
except Exception as e:
    logger.error(f"Erro ao criar OTLPSpanExporter: {e}")

FlaskInstrumentor().instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine)

app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    "/metrics": make_wsgi_app()
})

# ===== Routes =====
@app.route("/produtos", methods=["GET"])
def get_produtos():
    session = SessionLocal()
    try:
        produtos = session.query(Produto).all()
        return jsonify([produto_to_dict(p) for p in produtos])
    finally:
        session.close()

@app.route("/produtos", methods=["POST"])
def create_produto():
    data = request.get_json(force=True)
    session = SessionLocal()
    try:
        p = Produto(
            nome=data["nome"],
            preco=data["preco"],
            estoque=data.get("estoque",0),
            categoria_id=data.get("categoria_id")
        )
        session.add(p)
        session.commit()
        logger.info(f"Produto criado: {p.nome}")
        return jsonify(produto_to_dict(p)), 201
    except Exception as e:
        session.rollback()
        logger.error(f"Erro criar produto: {str(e)}")
        return jsonify({"error":"erro ao criar"}), 500
    finally:
        session.close()

@app.route("/produtos/<int:produto_id>", methods=["PUT"])
def update_produto(produto_id):
    data = request.get_json(force=True, silent=True)
    session = SessionLocal()
    try:
        p = session.get(Produto, produto_id)
        if not p: return jsonify({"error":"não encontrado"}), 404
        p.nome = data.get("nome", p.nome)
        p.preco = data.get("preco", p.preco)
        p.estoque = data.get("estoque", p.estoque)
        p.categoria_id = data.get("categoria_id", p.categoria_id)
        session.commit()
        session.refresh(p)
        logger.info(f"Produto atualizado: {p.nome}")
        return jsonify(produto_to_dict(p))
    except Exception as e:
        session.rollback()
        logger.error(f"Erro atualizar produto: {str(e)}")
        return jsonify({"error":"erro ao atualizar"}), 500
    finally:
        session.close()

@app.route("/produtos/<int:produto_id>", methods=["DELETE"])
def delete_produto(produto_id):
    session = SessionLocal()
    try:
        p = session.get(Produto, produto_id)
        if not p: return jsonify({"error":"não encontrado"}), 404
        session.delete(p)
        session.commit()
        logger.info(f"Produto deletado: {p.nome}")
        return jsonify({"ok": True})
    except Exception as e:
        session.rollback()
        logger.error(f"Erro deletar produto: {str(e)}")
        return jsonify({"error":"erro ao deletar"}), 500
    finally:
        session.close()

# ===============================
# FRONTEND
# ===============================
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    static_path = os.path.join(app.static_folder, path)
    if path and os.path.exists(static_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    if not wait_for_db():
        raise SystemExit("Banco não pronto")
    Base.metadata.create_all(bind=engine)
    logger.info(f"Servidor rodando na porta {PORT}")
    app.run(host="0.0.0.0", port=PORT)
