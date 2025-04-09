import random

def generate_job_id():
    return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=9))