import sys
from coffemodoro.app import CoffeodoroApp

def main():
    app = CoffeodoroApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
