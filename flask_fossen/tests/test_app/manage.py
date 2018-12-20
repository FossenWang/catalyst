import sys


def main():
    sys_argv = sys.argv
    if len(sys_argv) < 2:
        return 0

    from app import create_app
    app = create_app()

    if sys_argv[1] == 'shell':
        import code
        import logging
        from app.ext import db
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        with app.app_context():
            code.interact(local={'app': app, 'db': db})

    elif sys_argv[1] == 'run':
        if len(sys_argv) > 2 and sys_argv[2] == '-debug-off':
            debug = False
        else:
            debug = True
        app.run(debug=debug)

    elif sys_argv[1] == 'db':
        from app.ext import db
        from flask_migrate import Migrate, init, migrate, upgrade
        with app.app_context():
            Migrate(app, db)
            if len(sys_argv) < 3:
                raise NotImplementedError(
                    'input 3rd arg: init, migrate or upgrade')
            elif sys_argv[2] == 'init':
                init(directory='migrations')
            elif sys_argv[2] == 'migrate':
                migrate(directory='migrations')
            elif sys_argv[2] == 'upgrade':
                upgrade(directory='migrations')

    else:
        raise NotImplementedError('No such command')


if __name__ == '__main__':
    sys.path.append(sys.path[0].replace(r'\tests\test_app', ''))
    main()
