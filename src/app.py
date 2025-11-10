import os
import logging
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship
from sqlalchemy.exc import OperationalError

# Configurações
PORT = int(os.getenv("PORT", 5000))
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://meuuser:supersegredo@db:5432/minhadb"

app = Flask(__name__, static_folder="static", static_url_path="/static")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Banco
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()

# Modelos
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

# Helpers
def produto_to_dict(p: Produto):
    return {
        "id": p.id,
        "nome": p.nome,
        "preco": float(p.preco) if p.preco is not None else None,
        "estoque": p.estoque,
        "categoria": p.categoria.nome if p.categoria else None,
    }

# Rotas
@app.route("/produtos", methods=["GET"])
def get_produtos():
    session = SessionLocal()
    try:
        produtos = session.query(Produto).all()
        return jsonify([produto_to_dict(p) for p in produtos])
    except OperationalError:
        logger.warning("Banco de dados ainda não disponível.")
        return jsonify({"error": "banco de dados indisponível"}), 503
    finally:
        session.close()

@app.route("/produtos", methods=["POST"])
def create_produto():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "json inválido"}), 400

    nome = data.get("nome")
    preco_raw = data.get("preco")
    estoque = data.get("estoque", 0)
    categoria_id = data.get("categoria_id")

    if not nome or preco_raw is None:
        return jsonify({"error": "nome e preco são obrigatórios"}), 400

    try:
        preco = Decimal(str(preco_raw))
    except (InvalidOperation, ValueError):
        return jsonify({"error": "preco inválido"}), 400

    session = SessionLocal()
    try:
        p = Produto(nome=nome, preco=preco, estoque=int(estoque), categoria_id=categoria_id)
        session.add(p)
        session.commit()
        session.refresh(p)
        return jsonify({"id": p.id}), 201
    except OperationalError:
        logger.warning("Banco de dados indisponível — não foi possível criar produto.")
        return jsonify({"error": "banco de dados indisponível"}), 503
    except Exception as e:
        logger.exception("Erro ao criar produto: %s", e)
        session.rollback()
        return jsonify({"error": "erro ao criar produto"}), 500
    finally:
        session.close()

@app.route("/ui")
def ui_index():
    return send_from_directory(app.static_folder, "index.html")

# Inicialização
if __name__ == "__main__":
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas verificadas/criadas.")
    except OperationalError as e:
        logger.warning("Banco não disponível ainda (%s). Continuando mesmo assim.", e)

    logger.info("Iniciando servidor Flask na porta %d...", PORT)
    app.run(host="0.0.0.0", port=PORT)
