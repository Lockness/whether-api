import whether


def lambda_handler(event, _):
    params = event["pathParameters"]

    return whether.whether_handler(params)

