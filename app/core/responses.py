from http import HTTPStatus


notFoundResponse = {
    HTTPStatus.NOT_FOUND: {'description': HTTPStatus.NOT_FOUND.phrase}
}  # Any endpoint that calls "await Model.get()"
tooEarlyResponse = {HTTPStatus.TOO_EARLY: {'description': HTTPStatus.TOO_EARLY.phrase}}
conflictResponse = {HTTPStatus.CONFLICT: {'description': HTTPStatus.CONFLICT.phrase}}
badRequestResponse = {HTTPStatus.BAD_REQUEST: {'description': HTTPStatus.BAD_REQUEST.phrase}}

uploadErrorResponse = {
    HTTPStatus.UNSUPPORTED_MEDIA_TYPE: {'description': HTTPStatus.UNSUPPORTED_MEDIA_TYPE.phrase},
    HTTPStatus.SERVICE_UNAVAILABLE: {'description': HTTPStatus.SERVICE_UNAVAILABLE.phrase},
}
