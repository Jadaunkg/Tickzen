from app.automation_app import create_automation_app, create_automation_socketio

app = create_automation_app()
socketio = create_automation_socketio(app)

if __name__ == "__main__":
    socketio.run(app, debug=False, port=8081)
