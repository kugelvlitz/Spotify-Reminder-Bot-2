import timeit

# Test decorators


def timer(func):
    def wrapper(*args, **kwargs):
        """
            :param args:
            :param kwargs:
            :print: The tme it took to run func
            :return: wrapper
        """
        start = timeit.default_timer()
        do = func(*args, **kwargs)
        final = timeit.default_timer()
        print(final - start)
        return do

    return wrapper


def average(n):
    """
        :param n: times func is cycled
        :print:  average time func took to run in n cycles
        :return: repeat
    """
    def repeat(func):
        def wrapper(*args, **kwargs):
            """
            :param args:
            :param kwargs:
            :return: The average time out of n cycles of func
            """
            result = 0
            i = 0
            for i in range(n):
                start = timeit.default_timer()
                func(*args, **kwargs)
                final = timeit.default_timer()
                result += final - start
                i += 1
            print(result / i)

        return wrapper

    return repeat


def print_info(data):
    def print_master(func):
        def wrapper(*args, **kwargs):
            """
            :param args:
            :param kwargs:
            Hace la funcion e imprime master para mostrar cambios en el dict
            """
            func(*args, **kwargs)
            print(data)

        return wrapper

    return print_master
