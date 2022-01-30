import ulid

def lambda_handler(event, context):
    return {"ulid": str(ulid.new())}