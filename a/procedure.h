#define noreturn void __attribute__((__noreturn__))
typedef struct procedure    procedure_t;
typedef struct closure      closure_t;
typedef struct slot         slot_t;
typedef struct array        array_t;

typedef noreturn (*proc_t)(closure_t *closure, size_t argc, value_t *argv);

/*
 * procedure is a statically allocated structure along the function,
 * GC ignores procedure, so it doesn't have an object header or type.
 */
struct procedure
{
    proc_t      proc;
    long        iscont;
    const char *uid;
    size_t      varz;
    const char *vuid[];
};

struct closure
{
    object_t        object;
    procedure_t    *procedure;
    size_t          length;
    slot_t         *slot[];
};

struct slot
{
    object_t    object;
    value_t     value;
};

struct array
{
    object_t    object;
    size_t      length;
    value_t     value[];
};

#define DECLARATION(name) extern procedure_t name
#define DEFINITION(name, iscont, uid, z, vuid...) \
    noreturn name ## _proc(closure_t *closure, size_t argc, value_t *argv); \
    procedure_t name = {name ## _proc, iscont, uid, z, {vuid}}; \
    noreturn name ## _proc(closure_t *closure, size_t argc, value_t *argv)

#define ARGUMENT(index) (index<argc?argv[index]:null)
#define SLOT(index) (closure->slot[index])

#define VARGUMENT(index) ({ \
        long   i; \
        size_t length = 0; \
        size_t _index = (index); \
        if (index < argc) length = argc - _index; \
        array_t *array = newArray(length); \
        for (i = 0; i < length; i++) array->value[i] = argv[_index+i]; \
        (value_t)array;})
