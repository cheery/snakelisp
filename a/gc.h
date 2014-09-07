extern uint8_t* watermark;
extern uint64_t next_uid;

#define FRAMEPOINTER() ((uint8_t*)__builtin_frame_address(0))
#define GARBAGETRAP() \
    if (FRAMEPOINTER() < watermark) snakeGC(closure, argc, argv);

#define MAX_ROOTS 1024
extern size_t roots;
extern value_t root[MAX_ROOTS];

static inline value_t* plant(value_t value)
{
    assert(roots < MAX_ROOTS);
    root[roots] = value;
    return &root[roots++];
}

#define MAIN_ENTRY(entry) void main(int argc, char* argv[]) { snakeBoot(entry, argc, argv); }

noreturn snakeBoot(procedure_t *entry, int argc, char* argv[]);
noreturn snakeGC(closure_t *closure, size_t argc, value_t *argv);

#define T_MASK    0xFF00000000000000L
#define T_CLOSURE 0x0100000000000000L
#define T_SLOT    0x0200000000000000L
#define T_ARRAY   0x0300000000000000L

#define VECTORSIZE(vector) (sizeof(vector)/sizeof(*vector))

#define objectType(object) (((object_t*)(object))->tuid & T_MASK)

static inline void* _newObject(object_t *object, size_t type)
{
    assert(next_uid < T_MASK);
    object->to   = NULL;
    object->tuid = type | next_uid++;
    return object;
}

#define newObject(type, sz) (_newObject(alloca(sz), type))

#define newSlot(value_) ({ \
        slot_t *slot = newObject(T_SLOT, sizeof(slot_t)); \
        slot->value = value_; \
        slot;})

#define newArray(length) ({ \
        array_t *array = newObject(T_ARRAY, sizeof(array_t) + sizeof(value) * (length)); \
        array->length = length; \
        array;})

#define procClosure(proc, slots...) ({ \
        long i; \
        slot_t *slot[] = {slots}; \
        closure_t *closure = newObject(T_CLOSURE, sizeof(closure_t) + sizeof(slot)); \
        closure->procedure = proc; \
        closure->length = VECTORSIZE(slot); \
        for (i = 0; i < closure->length; i++) closure->slot[i] = slot[i]; \
        closure;})
