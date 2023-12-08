from flask import Flask, render_template, request

import marks as m


app = Flask(__name__)

# The arg  we pass in our .route is the url we would we can see the page


@app.route("/", methods=['GET', 'POST'])
def hello():
    count = 0
    if request.method == 'POST':
        hrs = request.form['hrs']
        marks_pred = m.marks_prediction(int(hrs))
        # mk = marks_pred
        print(marks_pred)

    return render_template('index.html')


# @app.route('/sub', methods=['POST'])
# def submit():
#     # we took from the html
#     if request.method == 'POST':
#         name = request.form['username']

#     # we take back to the html
#     return render_template('submit.html', n=name)


# To not rerun our server over and over again i.e to turn on the live watch, we can use the arg debug True
if __name__ == '__main__':
    app.run(debug=True)
