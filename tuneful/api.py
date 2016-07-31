import os.path
import json

from flask import request, Response, url_for, send_from_directory
from werkzeug.utils import secure_filename
from jsonschema import validate, ValidationError

from . import models
from . import decorators
from tuneful import app
from .database import session
from .utils import upload_path

# JSON Schema describing the structure of a song
song_schema = {
    "type": "object",
    "properties": {
        "file": {
            "type": "object",
            "properties": {
                "id": {"type": "number"}
            },
        },
    },
    "required": ["file"]
}

@app.route("/api/songs", methods=["GET"])
@decorators.accept("application/json")
def get_songs():
    """Return the list of songs"""
    # Get the songs from the database
    songs = session.query(models.Song).all()
    
    # Convert song list into JSON
    data = json.dumps([song.as_dictionary() for song in songs])
    return Response(data, 200, mimetype="application/json")
    
@app.route("/api/songs", methods=["POST"])
@decorators.accept("application/json")
@decorators.require("application/json")
def post_song():
    """Add a new song to the database"""
    data = request.json
    print(data)
    
    # Check that the JSON supplied is valid
    # If not you return a 422 Unprocessable Entity
    try:
        validate(data, song_schema)
    except ValidationError as error:
        data = {"message": error.message}
        return Response(json.dumps(data), 422, mimetype="application/json")
        
    # Add the song to the database
    song = models.Song(song_file_id=data["file"]["id"])
    session.add(song)
    session.commit()
    
    # Return a 201 Created, containing the post as JSON and with the
    # Location header set to the location of the post
    data = json.dumps(song.as_dictionary())
    headers = {"Location": url_for("get_songs", id=song.id)}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")
                    
@app.route("/api/files", methods=["POST"])
def post_song_file():
    """Add a new song to the database"""
    data = request.form
    print(data)
    print(request.files)
        
    # Add the file to the database note: the tests must be updated to accout for these occuring at the same time
    file = request.files.get("file")
    db_file = models.File(filename=file.filename)
    session.add(db_file)
    session.commit()
    
    song = models.Song()
    song.song_file = db_file
    session.add(song)
    session.commit()
    
    # Return a 201 Created, containing the post as JSON and with the
    # Location header set to the location of the post
    data = json.dumps(song.as_dictionary())
    headers = {"Location": url_for("get_songs", id=song.id)}
    return Response(data, 201, headers=headers,
                    mimetype="application/json")
                    
@app.route("/api/files/<int:id>", methods=["DELETE"])
@decorators.accept("application/json")
@decorators.require("application/json")
def delete_song(id):
    """Delete a song from the database"""
    song = session.query(models.Song).get(id)
    file = song.file
    
    # See if the song exists before deleting
    if not song:
        message = "A song with id {} does not exist".format(id)
        data = json.dumps({"Error": message})
        return Response(data, 404, mimetype="application/json")
        
    session.delete(song)
    session.delete(file)
    session.commit()
    
@app.route("/uploads/<filename>", methods=["GET"])
def uploaded_file(filename):
    return send_from_directory(upload_path(), filename)
    
@app.route("/api/files", methods=["POST"])
@decorators.require("multipart/form-data")
@decorators.accept("application/json")
def file_post():
    file = request.files.get("file")
    if not file:
        data = {"message": "Could not find file data"}
        return Response(json.dumps(data), 422, mimetype="application/json")

    filename = secure_filename(file.filename)
    db_file = models.File(filename=filename)
    session.add(db_file)
    session.commit()
    file.save(upload_path(filename))

    data = db_file.as_dictionary()
    return Response(json.dumps(data), 201, mimetype="application/json")