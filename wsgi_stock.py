from app.stock_app import create_stock_app, create_stock_socketio

app = create_stock_app()
socketio = create_stock_socketio(app)

if __name__ == "__main__":
    socketio.run(app, debug=False, port=5000)
