import os
import time
from flask import Flask, jsonify, request, send_from_directory, abort
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship

# Config
PORT = int(os.getenv("PORT", 5000))
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://meuuser:supersegredo@db:5432/minhadb"

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Banco
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()


# ===============================
# MODELOS
# ===============================
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


# ===============================
# HELPERS
# ===============================
def produto_to_dict(p: Produto):
    return {
        "id": p.id,
        "nome": p.nome,
        "preco": float(p.preco),
        "estoque": p.estoque,
        "categoria": p.categoria.nome if p.categoria else None,
    }


def wait_for_db(retries=20):
    """Tenta conectar no banco até estar pronto."""
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ Banco disponível")
            return True
        except Exception:
            print("⏳ DB não pronto, tentando novamente...")
            time.sleep(2)
    return False


# ===============================
# ROTAS API
# ===============================
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
            estoque=data.get("estoque", 0),
            categoria_id=data.get("categoria_id"),
        )
        session.add(p)
        session.commit()
        return jsonify(produto_to_dict(p)), 201
    except Exception as e:
        session.rollback()
        print("Erro ao criar produto:", e)
        return jsonify({"error": "erro ao criar produto"}), 500
    finally:
        session.close()


@app.route("/produtos/<int:produto_id>", methods=["PUT"])
def update_produto(produto_id):
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "json inválido"}), 400

    session = SessionLocal()
    try:
        p = session.get(Produto, produto_id)
        if not p:
            return jsonify({"error": "não encontrado"}), 404

        p.nome = data.get("nome", p.nome)
        p.preco = data.get("preco", p.preco)
        p.estoque = data.get("estoque", p.estoque)
        p.categoria_id = data.get("categoria_id", p.categoria_id)

        session.commit()
        session.refresh(p)
        return jsonify(produto_to_dict(p))
    except Exception as e:
        session.rollback()
        print("Erro ao atualizar produto:", e)
        return jsonify({"error": "erro ao atualizar"}), 500
    finally:
        session.close()


@app.route("/produtos/<int:produto_id>", methods=["DELETE"])
def delete_produto(produto_id):
    session = SessionLocal()
    try:
        p = session.get(Produto, produto_id)
        if not p:
            return jsonify({"error": "não encontrado"}), 404
        session.delete(p)
        session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        session.rollback()
        print("Erro ao deletar produto:", e)
        return jsonify({"error": "erro ao deletar"}), 500
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


# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    if not wait_for_db():
        raise SystemExit("❌ Banco não ficou pronto a tempo.")
    Base.metadata.create_all(bind=engine)
    print(f"🚀 Servidor rodando em http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT)
