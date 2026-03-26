import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import app, db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('  Database ready: portfolio.db')

    port = int(os.environ.get('PORT', 5000))
    print(f'\n  Portfolio Dashboard')
    print(f'  Open http://localhost:{port} in your browser\n')
    app.run(debug=False, host='0.0.0.0', port=port)
