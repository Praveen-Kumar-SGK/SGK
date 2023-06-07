import gc

class GarbageCollectorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        print("executing before view function")
        gc.disable()

        response = self.get_response(request)

        print("executing after view function")

        # Code to be executed for each request/response after
        # the view is called.
        gc.enable()
        garbagecollected = gc.collect()
        print("Garbage collector: collected %d objects." % (garbagecollected))

        return response