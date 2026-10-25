/* Minimal public client: no console, heap or application protocol code. */
#include "fujinet-nio.h"
FN_TIME_T clock_value;
volatile unsigned char clock_status;
int main(void)
{
    clock_status = fn_init();
    if (clock_status == FN_OK)
        clock_status = fn_clock_get(&clock_value);
    return clock_status;
}
