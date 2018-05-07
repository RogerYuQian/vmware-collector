class CollectorException(Exception):
    msg_fmt = None

    def __init__(self, message=None, **kwargs):
        if not message:
            message = self.msg_fmt % kwargs
        self.message = message
        super(CollectorException, self).__init__(message)

    def format_message(self):
        return self.args[0]


class PollException(CollectorException):
    pass


class ResourceNotFound(PollException):
    msg_fmt = '''resource: %(resource_id)s can not be found
in resource type: %(resource_type)s'''
