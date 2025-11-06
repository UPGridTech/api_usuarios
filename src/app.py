import os
import time
from flask import Flask, jsonify, request, send_from_directory
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session, relationship

PORT = int(os.getenv("PORT", 5000))
DATABASE_URL = os.getenv("DATABASE_URL")

app = Flask(__name__, static_folder="static", static_url_path="/static")

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
    preco = Column(Numeric(10,2), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias.id"))
    estoque = Column(Integer, default=0)
    categoria = relationship("Categoria", back_populates="produtos")

def wait_for_db(retries=20):
    for i in range(retries):
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except:
            print("DB não pronto, tentando novamente...")
            time.sleep(2)
    return False

# API Produtos
@app.route("/produtos", methods=["GET"])
def get_produtos():
    session = SessionLocal()
    try:
        produtos = session.query(Produto).all()
        return jsonify([{
            "id": p.id,
            "nome": p.nome,
            "preco": float(p.preco),
            "estoque": p.estoque,
            "categoria": p.categoria.nome if p.categoria else None
        } for p in produtos])
    finally:
        session.close()

@app.route("/produtos", methods=["POST"])
def create_produto():
    data = request.json
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
        return jsonify({"id": p.id}), 201
    finally:
        session.close()

# Serve Frontend
@app.route("/ui")
def ui_index():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    if not wait_for_db():
        raise SystemExit("DBB não ficou pronto")
    Base.metadata.create_all(bind=engine)
    app.run(host="0.0.0.0", port=PORT)
