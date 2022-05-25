from chdu_server import app

if __name__ == "__main__":
    os.system('cd ../hwc-matlab-client && git pull && hmd2html -s README.md -d ../html')
    os.system('mv ../html/README.html /var/www/hdu/html/index.html')
    os.system('rm -rv ../hwc-matlab-client/output')
    app.run()

