#include "snake.h"
#include "math.h"
#include <setjmp.h>
#include <sys/time.h>
#include <sys/resource.h>


#define SAFETY_PADDING (2*1024*1024)

uint8_t*    watermark;
uint64_t    next_uid = 0;
size_t      roots;
value_t     root[MAX_ROOTS];

static jmp_buf      stackreset;
static closure_t   *trap_closure;
static int          trap_argc;
static value_t     *trap_argv;

static void setWaterMark(uint8_t* high_mem)
{
    struct rlimit rlimit;
    size_t size;

    getrlimit(RLIMIT_STACK, &rlimit);
    size = rlimit.rlim_cur;

    if (size < SAFETY_PADDING*2)
    {
        watermark = high_mem - size / 2;
    }
    else
    {
        watermark = high_mem - size + SAFETY_PADDING;
    }
}

noreturn snakeBoot(procedure_t *entry, int argc, char* argv[])
{
    setWaterMark(FRAMEPOINTER());

    trap_closure = procClosure(entry);
    trap_argc = 0;
    trap_argv = NULL;
    setjmp(stackreset);
    trap_closure->procedure->proc(trap_closure, trap_argc, trap_argv);
}

/*
 * I'm used to implementing GC like this, when it cannot be tested.
 */
noreturn snakeGC(closure_t *closure, size_t argc, value_t *argv)
{
    assert(false);
    trap_closure = closure;
    trap_argc = argc;
    trap_argv = argv;
    longjmp(stackreset, 1);
}
