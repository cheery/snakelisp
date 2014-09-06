/*
 * This is supposed to be nan-coding, favoring pointers.
 */

typedef uint64_t value_t;

#define null  ((value_t)0)
#define dummy ((value_t)1)

#define T_OBJECT  0x0000000000000000L
#define T_BOOLEAN 0x0001000000000000L
#define T_FIXNUM  0x0002000000000000L
#define SIGN      0x0000800000000000L
#define NAN_OFFS  0x0007000000000000L
#define DATA_MASK 0x0000FFFFFFFFFFFFL

typedef struct object object_t;
struct object
{
    void*    to;
    uint64_t tuid; /* type and uid */
};

static inline int isNull(value_t value)
{
    return value == null;
}

static inline int isFalse(value_t value)
{
    return value == null || value == T_BOOLEAN;
}

static inline int isTrue(value_t value)
{
    return !isFalse(value);
}

static inline int isObject(value_t value)
{
    return (value & ~DATA_MASK) == T_OBJECT;
}

static inline int isBoolean(value_t value)
{
    return (value & ~DATA_MASK) == T_BOOLEAN;
}

static inline int isFixnum(value_t value)
{
    return (value & ~DATA_MASK) == T_FIXNUM;
}

static inline int isDouble(value_t value)
{
    return (value & ~DATA_MASK) >= NAN_OFFS;
}

static inline value_t boxDouble(double flonum)
{
    union pun { value_t value; double flonum; } pun;
    pun.flonum = flonum;
    pun.value += NAN_OFFS;
    assert(isDouble(pun.value));
    return pun.value;
}

static inline double unboxDouble(value_t value)
{
    union pun { value_t value; double flonum; } pun;
    pun.value = value - NAN_OFFS;
    return pun.flonum;
}

static inline value_t boxBoolean(int boolean)
{
    return T_BOOLEAN | (boolean?1:0);
}

static inline value_t boxFixnum(long fixnum)
{
    return T_FIXNUM | (DATA_MASK & fixnum);
}

static inline long unboxFixnum(value_t value)
{
    long data = value & DATA_MASK;
    return data | ((data & SIGN)?(~DATA_MASK):0);
}
