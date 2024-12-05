COLLECTION_SCHEMAS = {
    'rankings': {
        'validator': {
            '$jsonSchema': {
                'bsonType': 'object',
                'required': ['fecha', 'modulo', 'datos'],
                'properties': {
                    'fecha': {'bsonType': 'date'},
                    'modulo': {'bsonType': 'string'},
                    'datos': {'bsonType': 'array'}
                }
            }
        }
    }
} 