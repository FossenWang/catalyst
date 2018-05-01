import sys, traceback


def main():
    sys_argv = sys.argv
    if len(sys_argv) < 2:
        return 0

    from app import create_app
    app = create_app()

    if sys_argv[1] == 'shell':
        import code, logging
        from app.database import db
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        with app.app_context():
            code.interact(local={'app':app, 'db': db})

    elif sys_argv[1] == 'run':
        print(sys_argv)
        if len(sys_argv)>2 and sys_argv[2] == '-debug-off':
            debug = False
        else:
            debug = True
        app.run(debug=debug)
    else:
        raise NotImplementedError('No such command')

if __name__=='__main__':
    sys.path.append(sys.path[0].replace(r'\tests\test_app',''))
    main()