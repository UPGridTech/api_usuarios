from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os

app = Flask(__name__, static_folder="static", template_folder="static")

# Cockroach URL (cockroachdb://...)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------------------
#      MODELOS
# ---------------------------
class Categoria(db.Model):
    __tablename__ = "categorias"
    id = db.Column(db.String, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)


class Produto(db.Model):
    __tablename__ = "produtos"
    id = db.Column(db.String, primary_key=True)          # STRING → UUID
    nome = db.Column(db.String(200), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.String, db.ForeignKey("categorias.id"), nullable=True)


# ---------------------------
#      FRONTEND
# ---------------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ---------------------------
#      API CRUD PRODUTOS
# ---------------------------
@app.route("/produtos", methods=["GET"])
def get_produtos():
    produtos = Produto.query.all()
    return jsonify([
        {
            "id": str(p.id),
            "nome": p.nome,
            "preco": p.preco,
            "estoque": p.estoque,
            "categoria_id": str(p.categoria_id) if p.categoria_id else None
        }
        for p in produtos
    ])


@app.route("/produtos", methods=["POST"])
def create_produto():
    data = request.json

    novo_id = db.session.execute(text("SELECT gen_random_uuid()")).scalar()

    p = Produto(
        id=str(novo_id),
        nome=data["nome"],
        preco=data["preco"],
        estoque=data["estoque"],
        categoria_id=str(data["categoria_id"]) if data.get("categoria_id") else None
    )

    db.session.add(p)
    db.session.commit()

    return jsonify({"message": "Produto criado", "id": p.id})


@app.route("/produtos/<id>", methods=["PUT"])
def update_produto(id):
    produto = Produto.query.get(str(id))
    if not produto:
        return jsonify({"error": "Produto não encontrado"}), 404

    data = request.json
    produto.nome = data["nome"]
    produto.preco = data["preco"]
    produto.estoque = data["estoque"]
    produto.categoria_id = str(data["categoria_id"]) if data.get("categoria_id") else None

    db.session.commit()
    return jsonify({"message": "Atualizado"})


@app.route("/produtos/<id>", methods=["DELETE"])
def delete_produto(id):
    produto = Produto.query.get(str(id))
    if not produto:
        return jsonify({"error": "Produto não encontrado"}), 404

    db.session.delete(produto)
    db.session.commit()
    return jsonify({"message": "Deletado"})


# ---------------------------
#      API CATEGORIAS
# ---------------------------
@app.route("/categorias", methods=["GET"])
def get_categorias():
    categorias = Categoria.query.all()
    return jsonify([
        {"id": str(c.id), "nome": c.nome} for c in categorias
    ])


# ---------------------------
#      RUN
# ---------------------------
if __name__ == "__main__":
    # Cria tabelas se não existirem
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000)
