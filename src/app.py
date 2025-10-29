from flask import Flask, jsonify, request

app = Flask(__name__)

# Simulação de um banco de dados (lista)
usuarios = [
    {"id": 1, "nome": "Jhennifer", "email": "jhennifer@email.com"},
    {"id": 2, "nome": "Samuel", "email": "samuel2222@email.com"}
    {"id": 3, "nome": "Felipe", "email": "felipeee22e@email.com"}
]

# Rota raiz
@app.route("/")
def home():
    return jsonify({"mensagem": "API de Usuários está rodando 🚀"})

# Listar todos os usuários
@app.route("/usuarios", methods=["GET"])
def listar_usuarios():
    return jsonify(usuarios)

# Obter usuário por ID
@app.route("/usuarios/<int:id>", methods=["GET"])
def obter_usuario(id):
    usuario = next((u for u in usuarios if u["id"] == id), None)
    if usuario:
        return jsonify(usuario)
    return jsonify({"erro": "Usuário não encontrado"}), 404

# Criar novo usuário
@app.route("/usuarios", methods=["POST"])
def criar_usuario():
    novo = request.json
    novo["id"] = len(usuarios) + 1
    usuarios.append(novo)
    return jsonify(novo), 201

# Atualizar usuário existente
@app.route("/usuarios/<int:id>", methods=["PUT"])
def atualizar_usuario(id):
    usuario = next((u for u in usuarios if u["id"] == id), None)
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    dados = request.json
    usuario.update(dados)
    return jsonify(usuario)

# Deletar usuário
@app.route("/usuarios/<int:id>", methods=["DELETE"])
def deletar_usuario(id):
    global usuarios
    usuarios = [u for u in usuarios if u["id"] != id]
    return jsonify({"mensagem": f"Usuário {id} removido com sucesso!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

