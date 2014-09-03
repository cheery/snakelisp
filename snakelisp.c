#include "snakelisp.h"
#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <math.h>
#include <setjmp.h>
#include <sys/time.h>
#include <sys/resource.h>

static CONTINUATION(call_cc_continue)
{
    call(*SLOT(0), ARG(2));
}

static CONTINUATION(call_cc)
{
    value_t cont = ARG(1);
    value_t func = spawnClosure(call_cc_continue, &cont);
    call(ARG(2), func);
}

static CONTINUATION(pick)
{
    if (unboxBoolean(ARG(2)))
    {
        call(ARG(3), ARG(1));
    }
    else
    {
        call(ARG(4), ARG(1));
    }
}

static CONTINUATION(new_array)
{
    call(ARG(1), boxArray(newArray(ARG_INTEGER(2))));
}

static CONTINUATION(new_arraybuffer)
{
    call(ARG(1), boxArrayBuffer(newArrayBuffer(ARG_INTEGER(2))));
}

static CONTINUATION(file_open)
{
    int fd;
    string_t *path = ARG_STRING(2);
    fd = open(path->data, O_RDONLY);
    call(ARG(1), boxInteger(fd));
}

static CONTINUATION(file_close)
{
    close(ARG_INTEGER(2));
    call(ARG(1), boxNull());
}

static CONTINUATION(file_read)
{
    int fd = ARG_INTEGER(2);
    arraybuffer_t *buffer = ARG_ARRAYBUFFER(3);
    size_t count = buffer->length;
    if (argc > 4) count = ARG_INTEGER(4);
    count = read(fd, buffer->data, count);
    call(ARG(1), boxInteger(count));
}

static CONTINUATION(file_write)
{
    int fd = ARG_INTEGER(2);
    size_t count;
    void  *data;
    if (isArrayBuffer(ARG(3)))
    {
        arraybuffer_t *arraybuffer = ARG_ARRAYBUFFER(3);
        data  = arraybuffer->data;
        count = arraybuffer->length;
    }
    else if (isString(ARG(3)))
    {
        string_t *string = ARG_STRING(3);
        data  = string->data;
        count = string->length;
    }
    else
    {
        ARG_ERROR(3, "arraybuffer or string");
    }
    if (argc > 4) count = ARG_INTEGER(4);
    call(ARG(1), boxInteger(write(fd, data, count)));
}

static CONTINUATION(catenate)
{
    size_t i = 2;
    size_t length = 1;
    size_t offset = 0;
    switch(ARG(2).type)
    {
        case TYPE_STRING:
            {
                for(i = 2; i < argc; i++)
                {
                    length += ARG_STRING(i)->length;
                }
                string_t *result = newString(length, NULL);
                string_t *current;
                for(i = 2; i < argc; i++)
                {
                    current = unboxString(ARG(i));
                    memcpy(&result->data[offset], current->data, current->byteLength);
                    offset += current->length;
                }
                call(ARG(1), boxString(result));
            }
            break;
        default:
            ARG_ERROR(i, "string");
    }
}

static CONTINUATION(length_of)
{
    size_t length;
    switch(ARG(2).type)
    {
        case TYPE_STRING:
            length = ARG_STRING(2)->length;
            break;
        case TYPE_ARRAYBUFFER:
            length = ARG_ARRAYBUFFER(2)->length;
            break;
        case TYPE_ARRAY:
            length = ARG_ARRAY(2)->length;
            break;
        default:
            ARG_ERROR(2, "array, arraybuffer or string");
    }
    call(ARG(1), boxInteger(length));
}

static CONTINUATION(load_idx)
{
    size_t index = ARG_INTEGER(3);
    switch(ARG(2).type)
    {
        case TYPE_STRING:
            {
                string_t *string = ARG_STRING(2);
                if (index >= string->length) assert(1==2);
                call(ARG(1), boxString(newString(1, &string->data[index])));
            }
            break;
        case TYPE_ARRAYBUFFER:
            {
                arraybuffer_t *arraybuffer = ARG_ARRAYBUFFER(2);
                if (index >= arraybuffer->length) assert(1==2);
                call(ARG(1), boxInteger(arraybuffer->data[index]));
            }
            break;
        case TYPE_ARRAY:
            {
                array_t *array = ARG_ARRAY(2);
                if (index >= array->length) assert(1==2);
                call(ARG(1), array->val[index]);
            }
            break;
        default:
            ARG_ERROR(2, "array, arraybuffer or string");
    }
}

static CONTINUATION(store_idx)
{
    size_t index = ARG_INTEGER(3);
    switch(ARG(2).type)
    {
        case TYPE_ARRAY:
            {
                array_t *array = ARG_ARRAY(2);
                if (index >= array->length) assert(1==2);
                array->val[index] = ARG(4);
            }
            break;
        case TYPE_ARRAYBUFFER:
            {
                arraybuffer_t *arraybuffer = ARG_ARRAYBUFFER(2);
                if (index >= arraybuffer->length) assert(1==2);
                arraybuffer->data[index] = ARG_INTEGER(4);
            }
            break;
        default:
            ARG_ERROR(2, "array or arraybuffer");
    }
    call(ARG(1), ARG(4));
}

static CONTINUATION(is_closure)
{
    call(ARG(1), boxBoolean(isClosure(ARG(2))));
}

static CONTINUATION(is_null)
{
    call(ARG(1), boxBoolean(isNull(ARG(2))));
}

static CONTINUATION(is_true)
{
    call(ARG(1), boxBoolean(isTrue(ARG(2))));
}

static CONTINUATION(is_false)
{
    call(ARG(1), boxBoolean(isFalse(ARG(2))));
}

static CONTINUATION(is_boolean)
{
    call(ARG(1), boxBoolean(isBoolean(ARG(2))));
}

static CONTINUATION(is_integer)
{
    call(ARG(1), boxBoolean(isInteger(ARG(2))));
}

static CONTINUATION(is_double)
{
    call(ARG(1), boxBoolean(isDouble(ARG(2))));
}

static CONTINUATION(is_array)
{
    call(ARG(1), boxBoolean(isArray(ARG(2))));
}

static CONTINUATION(is_arraybuffer)
{
    call(ARG(1), boxBoolean(isArrayBuffer(ARG(2))));
}

static CONTINUATION(is_string)
{
    call(ARG(1), boxBoolean(isString(ARG(2))));
}

#define COMPARATOR(op) \
{ \
    long truth = false; \
    value_t a = ARG(2); \
    value_t b = ARG(3); \
 \
    if (coercesToInteger(a) && coercesToInteger(b)) \
    { \
        truth = ARG_INTEGER(2) op ARG_INTEGER(3); \
    } \
    else if (coercesToDouble(a) && coercesToDouble(b)) \
    { \
        truth = ARG_DOUBLE(2) op ARG_DOUBLE(3); \
    } \
    else if (isString(a) && isString(b)) \
    { \
        string_t *astr = ARG_STRING(2); \
        string_t *bstr = ARG_STRING(3); \
        truth = (strcmp(astr->data, bstr->data) op 0); \
    } \
    else \
    { \
        assert(false); /* not implemented for this value pair. */ \
    } \
    call(ARG(1), boxBoolean(truth)); \
}

static CONTINUATION(op_lt) COMPARATOR(<)
static CONTINUATION(op_le) COMPARATOR(<=)
static CONTINUATION(op_gt) COMPARATOR(>)
static CONTINUATION(op_ge) COMPARATOR(>=)

static CONTINUATION(op_eq)
{
    long truth = false;
    value_t a = ARG(2);
    value_t b = ARG(3);

    if (coercesToInteger(a) && coercesToInteger(b))
    {
        truth = ARG_INTEGER(2) == ARG_INTEGER(3);
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        truth = ARG_DOUBLE(2) == ARG_DOUBLE(3);
    }
    else if (isString(a) && isString(b))
    {
        string_t *astr = ARG_STRING(2);
        string_t *bstr = ARG_STRING(3);
        truth = (strcmp(astr->data, bstr->data) == 0);
    }
    else
    {
        truth = (a.type == b.type) && (a.a.address == b.a.address);
    }
    call(ARG(1), boxBoolean(truth));
}

static CONTINUATION(op_ne)
{
    long truth = false;
    value_t a = ARG(2);
    value_t b = ARG(3);

    if (coercesToInteger(a) && coercesToInteger(b))
    {
        truth = ARG_INTEGER(2) != ARG_INTEGER(3);
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        truth = ARG_DOUBLE(2) != ARG_DOUBLE(3);
    }
    else if (isString(a) && isString(b))
    {
        string_t *astr = ARG_STRING(2);
        string_t *bstr = ARG_STRING(3);
        truth = (strcmp(astr->data, bstr->data) != 0);
    }
    else
    {
        truth = (a.type != b.type) || (a.a.address != b.a.address);
    }
    call(ARG(1), boxBoolean(truth));
}




static CONTINUATION(op_add)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) + ARG_INTEGER(3)));
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        call(ARG(1), boxDouble(ARG_DOUBLE(2) + ARG_DOUBLE(3)));
    }
    else
    {
        ARG_ERROR(2, "integer or double");
    }
}

static CONTINUATION(op_sub)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) - ARG_INTEGER(3)));
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        call(ARG(1), boxDouble(ARG_DOUBLE(2) - ARG_DOUBLE(3)));
    }
    else
    {
        ARG_ERROR(2, "integer or double");
    }
}

static CONTINUATION(op_mul)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) * ARG_INTEGER(3)));
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        call(ARG(1), boxDouble(ARG_DOUBLE(2) * ARG_DOUBLE(3)));
    }
    else
    {
        ARG_ERROR(2, "integer or double");
    }
}

static CONTINUATION(op_div)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) / ARG_INTEGER(3)));
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        call(ARG(1), boxDouble(ARG_DOUBLE(2) / ARG_DOUBLE(3)));
    }
    else
    {
        ARG_ERROR(2, "integer or double");
    }
}

static CONTINUATION(op_floordiv)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) / ARG_INTEGER(3)));
    }
    else if (coercesToDouble(a) && coercesToDouble(b))
    {
        call(ARG(1), boxInteger(ARG_DOUBLE(2) / ARG_DOUBLE(3)));
    }
    else
    {
        ARG_ERROR(2, "integer or double");
    }
}

static CONTINUATION(op_modulus)
{
    value_t a = ARG(2);
    value_t b = ARG(3);
    if (coercesToInteger(a) && coercesToInteger(b))
    {
        call(ARG(1), boxInteger(ARG_INTEGER(2) % ARG_INTEGER(3)));
    }
//  need to figure out nice way to this later on.
//    else if (coercesToDouble(a) && coercesToDouble(b))
//    {
//        call(ARG(1), boxInteger(ARG_DOUBLE(2) % ARG_DOUBLE(3)));
//    }
    else
    {
        ARG_ERROR(2, "integer");
    }
}

static CONTINUATION(to_character)
{
    char ch = ARG_INTEGER(2);
    call(ARG(1), boxString(newString(1, &ch)));
}

static CONTINUATION(to_ordinal)
{
    string_t *a = ARG_STRING(2);
    if (a->length == 0)
    {
        call(ARG(1), boxNull());
    }
    else
    {
        call(ARG(1), boxInteger(a->data[0]));
    }
}

static CONTINUATION(op_and)
{
    size_t i;
    long truth = true;
    for (i = 2; i < argc; i++) truth = truth && ARG_BOOLEAN(i);
    call(ARG(1), boxBoolean(truth));
}

static CONTINUATION(op_or)
{
    size_t i = 2;
    long truth = false;
    for (i = 2; i < argc; i++) truth = truth || ARG_BOOLEAN(i);
    call(ARG(1), boxBoolean(truth));
}

static CONTINUATION(op_not)
{
    call(ARG(1), boxBoolean(!ARG_BOOLEAN(2)));
}

static CONTINUATION(op_lsh)
{
    call(ARG(1), boxInteger(ARG_INTEGER(2) << ARG_INTEGER(3)));
}

static CONTINUATION(op_rsh)
{
    call(ARG(1), boxInteger(ARG_INTEGER(2) >> ARG_INTEGER(3)));
}

static CONTINUATION(op_bit_or)
{
    call(ARG(1), boxInteger(ARG_INTEGER(2) | ARG_INTEGER(3)));
}
static CONTINUATION(op_bit_and)
{
    call(ARG(1), boxInteger(ARG_INTEGER(2) & ARG_INTEGER(3)));
}

static CONTINUATION(op_bit_xor)
{
    call(ARG(1), boxInteger(ARG_INTEGER(2) ^ ARG_INTEGER(3)));
}

static CONTINUATION(op_bit_not)
{
    call(ARG(1), boxInteger(~ARG_INTEGER(2)));
}

static CONTINUATION(op_log)
{
    call(ARG(1), boxDouble(log(ARG_DOUBLE(2))));
}

static CONTINUATION(op_exp)
{
    call(ARG(1), boxDouble(exp(ARG_DOUBLE(2))));
}

static CONTINUATION(op_pow)
{
    call(ARG(1), boxDouble(pow(ARG_DOUBLE(2), ARG_DOUBLE(3))));
}

static CONTINUATION(op_sqrt)
{
    call(ARG(1), boxDouble(sqrt(ARG_DOUBLE(2))));
}

value_t
    *p_get_interface,
    *p_set_interface,
    *p_closure_interface,
    *p_numeric_interface,
    *p_string_interface,
    *p_arraybuffer_interface;

static CONTINUATION(get_interface)
{
    value_t value = ARG(2);
    value_t interface;
    switch (value.type)
    {
        case TYPE_CLOSURE:
            interface = *p_closure_interface;
            break;
        case TYPE_BOOLEAN:
        case TYPE_INTEGER:
        case TYPE_DOUBLE:
            interface = *p_numeric_interface;
            break;
        case TYPE_STRING:
            interface = *p_string_interface;
            break;
        case TYPE_ARRAYBUFFER:
            interface = *p_arraybuffer_interface;
            break;
        case TYPE_ARRAY:
            interface = ARG_ARRAY(2)->interface;
            break;
        default:
            assert(false);
    }
    call(ARG(1), interface);
}

static CONTINUATION(set_interface)
{
    array_t *array = ARG_ARRAY(2);
    array->interface = ARG(3);
    call(ARG(1), ARG(2));
}

size_t rootz = 0;
value_t root[MAX_ROOTS];

static inline value_t* newRoot(const char *name, value_t value)
{
    value_t* ptr = &root[rootz];
    root[rootz++] = value;
    assert(rootz < MAX_ROOTS);
    return ptr;
}

value_t uncallable_hook;
value_t type_error_hook;
value_t error_quit;

uint8_t* gc_high;
uint8_t* gc_watermark;
static jmp_buf gc_flush;
static closure_t* gc_closure;
static int gc_argc;
static value_t *gc_argv;

static inline size_t stackSize()
{
    struct rlimit rlimit;
    getrlimit(RLIMIT_STACK, &rlimit);
    return rlimit.rlim_cur;
}

void adjustWaterMark(uint8_t* address)
{
    size_t sz = stackSize();
    size_t pad = 2*1024*1024;
    size_t limit = sz - pad;
    if (sz < pad*2)
    {
        limit = sz / 2;
    }
    gc_high = address;
    gc_watermark = (address - limit);
}

static CONTINUATION(quit)
{
    uint8_t* a = frameAddress();
    printf("used: %li, avail: %li\n", gc_high-a, a-gc_watermark);
    exit(0);
}

static CONTINUATION(errorQuit)
{
    exit(1);
}

void initGC();
void snakeBoot(value_t entry)
{
    adjustWaterMark(frameAddress());
    initGC();

    if (setjmp(gc_flush))
    {
        gc_closure->proc(gc_closure, gc_argc, gc_argv);
        return;
    }

    uncallable_hook = boxNull();
    type_error_hook = boxNull();

    newRoot("stdin",  boxInteger(0));
    newRoot("stdout", boxInteger(1));
    newRoot("stderr", boxInteger(2));
    newRoot("file-open", spawnClosure(file_open));
    newRoot("file-read", spawnClosure(file_read));
    newRoot("file-write", spawnClosure(file_write));
    newRoot("file-close", spawnClosure(file_close));
    newRoot("call/cc", spawnClosure(call_cc));
    newRoot("pick", spawnClosure(pick));
    newRoot("array", spawnClosure(new_array));
    newRoot("arraybuffer", spawnClosure(new_arraybuffer));

    newRoot("cat", spawnClosure(catenate));
    newRoot("length", spawnClosure(length_of));
    newRoot("idx", spawnClosure(load_idx));
    newRoot("idx=", spawnClosure(store_idx));

    newRoot("closure?", spawnClosure(is_closure));
    newRoot("null?", spawnClosure(is_null));
    newRoot("true?", spawnClosure(is_true));
    newRoot("false?", spawnClosure(is_false));
    newRoot("boolean?", spawnClosure(is_boolean));
    newRoot("integer?", spawnClosure(is_integer));
    newRoot("double?", spawnClosure(is_double));
    newRoot("array?", spawnClosure(is_array));
    newRoot("arraybuffer?", spawnClosure(is_arraybuffer));
    newRoot("string?", spawnClosure(is_string));
    newRoot("=", spawnClosure(op_eq));
    newRoot("!=", spawnClosure(op_ne));
    newRoot("<", spawnClosure(op_lt));
    newRoot("<=", spawnClosure(op_le));
    newRoot(">", spawnClosure(op_gt));
    newRoot(">=", spawnClosure(op_ge));
    newRoot("+", spawnClosure(op_add));
    newRoot("-", spawnClosure(op_sub));
    newRoot("*", spawnClosure(op_mul));
    newRoot("/", spawnClosure(op_div));
    newRoot("//", spawnClosure(op_floordiv));
    newRoot("%", spawnClosure(op_modulus));
    newRoot("chr", spawnClosure(to_character));
    newRoot("ord", spawnClosure(to_ordinal));
    newRoot("and", spawnClosure(op_and));
    newRoot("or", spawnClosure(op_or));
    newRoot("not", spawnClosure(op_not));
    newRoot("<<", spawnClosure(op_lsh));
    newRoot(">>", spawnClosure(op_rsh));
    newRoot("|", spawnClosure(op_bit_or));
    newRoot("&", spawnClosure(op_bit_and));
    newRoot("^", spawnClosure(op_bit_xor));
    newRoot("~", spawnClosure(op_bit_not));
    newRoot("log", spawnClosure(op_log));
    newRoot("exp", spawnClosure(op_exp));
    newRoot("pow", spawnClosure(op_pow));
    newRoot("sqrt", spawnClosure(op_sqrt));

    p_get_interface = newRoot("interface", spawnClosure(get_interface));
    p_set_interface = newRoot("interface=", spawnClosure(set_interface));
    p_closure_interface = newRoot("closure-interface", boxNull());
    p_numeric_interface = newRoot("numeric-interface", boxNull());
    p_string_interface = newRoot("string-interface", boxNull());
    p_arraybuffer_interface = newRoot("arraybuffer-interface", boxNull());

    error_quit = spawnClosure(errorQuit);
    call(entry, spawnClosure(quit));
}

static size_t fr_spacez = 0;
static size_t to_spacez = 0;
static char* fr_space = NULL;
static char* to_space = NULL;
static char* to_next = NULL;
void initGC()
{
}

static void flipGC()
{
    char* tmp;
    size_t tmpz;

    tmpz = fr_spacez;
    tmp  = fr_space;
    fr_space  = to_space;
    fr_spacez = to_spacez;
    to_space = tmp;
    to_spacez = tmpz;
}

static void* shiftMem(size_t size)
{
    assert(size > 0);
    void* address = to_next;
    to_next += size;
    return address;
}

static void* copyObject(void* address, uint8_t type)
{
    object_t *obj = address;
    if(obj->to)
    {
        return obj->to;
    } else
    {
        obj->to = (void*)(long)type;
        obj->to = memcpy(shiftMem(obj->size), address, obj->size);
    }
}

static inline value_t updatePointer(value_t value)
{
    if (isNull(value)) return value;
    if (value.type == TYPE_BOOLEAN
            || value.type == TYPE_INTEGER
            || value.type == TYPE_DOUBLE) return value;
    value.a.address = copyObject(value.a.address, value.type);
    return value;
}

static inline value_t* updateSlot(value_t *value)
{
    struct slot *slot;
    if (value->type == TYPE_SLOTCOPY) return value->a.address;
    *value = updatePointer(*value);
    
    slot = shiftMem(sizeof(struct slot));
    slot->object.to = (void*)TYPE_SLOTCOPY;
    slot->object.size = sizeof(struct slot);
    slot->slot = *value;

    value->type = TYPE_SLOTCOPY;
    value->a.address = &slot->slot;
    return value->a.address;
}

#define ROOT(x) (x = updatePointer(x))

void snakeGC(closure_t *closure, size_t argc, value_t *argv)
{
    char* next;
    object_t *obj;
    closure_t *cl;
    array_t   *arr;
    uint8_t type;
    int i;

    flipGC();
    to_spacez = (gc_high - gc_watermark) + fr_spacez;
    to_space  = realloc(to_space, to_spacez);
    to_next   = to_space;
    next      = to_space;
    closure = copyObject(closure, TYPE_CLOSURE);
    for(i = 0; i < argc; i++) argv[i] = updatePointer(argv[i]);

    for(i = 0; i < rootz; i++) root[i] = updatePointer(root[i]);
    // make this bit more maintainable later...
    ROOT(uncallable_hook);
    ROOT(type_error_hook);
    ROOT(error_quit);

    while(next < to_next)
    {
        obj = (object_t*)next;
        next += obj->size;
        type = (long)obj->to;
        obj->to = NULL;
        switch (type)
        {
            case TYPE_ARRAY:
                arr = (array_t*)obj;
                for (i = 0; i < arr->length; i++) arr->val[i] = updatePointer(arr->val[i]);
                break;
            case TYPE_CLOSURE:
                assert(obj->size > 0);
                cl = (closure_t*)obj;
                for (i = 0; i < cl->length; i++) cl->slot[i] = updateSlot(cl->slot[i]);
                break;
            case TYPE_SLOTCOPY:
            case TYPE_ARRAYBUFFER:
            case TYPE_STRING:
                break;
            default:
                printf("missing gc handler\n");
                assert(false);
        }
    }

    gc_closure = closure;
    gc_argc = argc;
    gc_argv = memcpy(shiftMem(sizeof(value_t)*argc), argv, sizeof(value_t)*argc);
    longjmp(gc_flush, 1);
}
