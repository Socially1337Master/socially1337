from flask import Flask; import random; app = Flask(__name__); app.add_url_rule('/', 'index', lambda: random.choice(["¯\_(ツ)_/¯", "(ง'̀-'́)ง", "(•_•) ( •_•)>⌐■-■ (⌐■_■)", "(☞ﾟヮﾟ)☞ ☜(ﾟヮﾟ☜)"])); app.run(host='0.0.0.0', port=1337)
