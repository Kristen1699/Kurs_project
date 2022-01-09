#!flask/bin/python
from flask import Flask, jsonify, abort, request, make_response
import os.path
from tempfile import NamedTemporaryFile
from PIL import Image

app = Flask(__name__)
tasks = []


@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/api/v1.0/info/<int:task_id>', methods=['GET'])# получение размера и названия по id
def get_task(task_id):
    task = next((x for x in tasks if x["id"] == task_id), None)
    if task is None:
        abort(404)
    return jsonify({'size': os.path.getsize(task['file'])}, {'name': task['name']})


@app.route('/baranova/api/v1.0/image_id/<int:task_id>', methods=['GET'])# получение файла по id
def get_image_id(task_id):
    task = next((x for x in tasks if x["id"] == task_id), None)
    if task is None:
        abort(404)
    with open(task['file'], 'rb') as fp:
        image_binary = fp.read()
    response = make_response(image_binary)
    response.headers.set('Content-Type', 'image/%s' % task['image_type'])
    response.headers.set(
        'Content-Disposition', 'attachment', filename='%s' % task['name'] + '.' + task['image_type'])
    return response


@app.route('/baranova/api/v1.0/image_name/<string:task_name>', methods=['GET'])# получение файла по имени
def get_image_name(task_name):
    task = next((x for x in tasks if x["name"] == task_name), None)
    if task is None:
        abort(404)
    with open(task['file'], 'rb') as fp:
        image_binary = fp.read()
    response = make_response(image_binary)
    response.headers.set('Content-Type', 'image/%s' % task['image_type'])
    response.headers.set(
        'Content-Disposition', 'attachment', filename='%s' % task['name'] + '.' + task['image_type'])
    return response


@app.route('/baranova/api/v1.0/bgr', methods=['GET'])# получение измененного файла-изображения
def get_bgr():
    if len(tasks) <= 0:
        abort(404)
    files = []
    for task in tasks:
        files.append(task['file'])
    images = [Image.open(x) for x in files]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    r, g, b = new_im.split()
    new_im = Image.merge('RGB', (b, g, r))

    new_im.save('bgr.jpeg')
    with open('bgr.jpeg', 'rb') as fp:
        image_binary = fp.read()
    response = make_response(image_binary)
    response.headers.set('Content-Type', 'image/jpeg')
    response.headers.set(
        'Content-Disposition', 'attachment', filename='bgr.jpeg')
    return response


@app.route('/baranova/api/v1.0/send', methods=['POST'])# загрузка данных на сервер
def create_task():
    if request.files.__len__() != 1:
        abort(400)
    for file in request.files:
        if request.files[file].content_type.partition('/')[0] != 'image':
            abort(400)
        if len(tasks) == 0:
            id_file = 1
        else:
            id_file = tasks[-1]['id'] + 1
        request.files[file].stream.fileno()
        temp_file = NamedTemporaryFile(delete=False)
        temp_file.write(request.files[file].stream.read())
        task = {
            'id': id_file,
            'file': temp_file.name,
            'name': file,
            'image_type': request.files[file].content_type.partition('/')[2]
        }
        tasks.append(task)

        return jsonify({'id': id_file}, {'name': file}), 201


@app.route('/baranova/api/v1.0/delete/<int:task_id>', methods=['DELETE'])# удаление данных по id
def delete_task(task_id):
    task = next((x for x in tasks if x["id"] == task_id), None)
    if task is None:
        abort(404)
    tasks.remove(task)
    return jsonify({'result': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0')