import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('  Database ready: portfolio.db')

    print('\n  Portfolio Dashboard')
    print('  Open http://localhost:5051 in your browser\n')
    app.run(debug=True, host='0.0.0.0', port=5051)
