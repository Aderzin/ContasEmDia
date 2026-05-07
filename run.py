from api.index import app

if __name__ == "__main__":
    # O modo debug=True permite que o site atualize sozinho
    # toda vez que você salvar uma alteração no código.
    app.run(debug=True, port=5000)