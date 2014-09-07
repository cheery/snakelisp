#define call(callee, args...) ({ \
        value_t _args[] = {args}; \
        _call(callee, VECTORSIZE(_args), _args); \
        })

#define vcall(callee, array, args...) ({ \
        value_t _args[] = {args}; \
        _vcall(callee, array, VECTORSIZE(_args), _args); \
        })

static inline noreturn _call(value_t callee, size_t argc, value_t *argv)
{
    if (isObject(callee))
    {
        closure_t *closure = (closure_t*)callee;
        if (objectType(callee) == T_CLOSURE)
        {
            closure->procedure->proc(closure, argc, argv);
        }
    }
    assert(false);
}

static inline noreturn _vcall(value_t callee, value_t array, size_t argc, value_t *argv)
{
    size_t i;
    if ((!isObject(array)) || (objectType(array) != T_ARRAY))
    {
        assert(false);
    }
    array_t* _array = (array_t*)array;
    size_t _argc = argc + _array->length;
    value_t _argv[_argc];
    for (i = 0; i < _argc; i++) _argv[i] = argv[i];
    for (i = 0; i < _array->length; i++) _argv[argc+i] = _array->value[i];
    _call(callee, _argc, _argv);
}
