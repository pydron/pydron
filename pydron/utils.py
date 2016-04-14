from twisted.python import threadable

def is_reactor_thread():
    """
    Attempts to find out if the calling thread is the reactor thread.
    """
    return threadable.isInIOThread()
    