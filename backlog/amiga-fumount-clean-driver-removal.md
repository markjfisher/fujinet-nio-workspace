## Extensions to support unloading device drivers and dismounting network drives cleanly

## Question 1
I have developed a network driver for the amiga, which is loaded as a resident driver. Is there a clean way to unload it without rebooting the amiga? The resident loader code is at 
fujinet-load-resident.c In the user startup it loads "fujinet-nio.device" 
fujinet_nio_device.c and "fujinet-disk.device"  fujinet_disk_device.c


## Answer 1

Yes — for fujinet-nio.device, you’re already very close to supporting a clean unload.

The standard Exec mechanism is RemDevice(). The RKM says RemDevice() calls the device’s Expunge vector; the device may defer if it is open/busy, otherwise it should tear itself down and return the original segment list so Exec can unload disk-loaded code. The modern AmigaOS docs say the same thing explicitly: if the device came from disk, the system uses the returned seglist to unload its code.

Your loader is already doing the right foundational thing:

segment_list = LoadSeg(module);
...
initialized = InitResident(resident, (ULONG)segment_list);

So the device receives the actual LoadSeg() seglist, which is exactly what InitResident() expects for a disk-loaded device.

More importantly, your current fujinet-nio.device already stores that seglist:

base->segment_list = segment_list;

and its device_expunge() eventually returns it. It also refuses immediate expunge while there are opens, queued requests, or an in-progress request, setting LIBF_DELEXP instead. Then the final CloseDevice() path completes the delayed expunge.

So I would add a little CLI utility, perhaps:

fujinet-unload-resident fujinet-nio.device

whose core is essentially the RKM's own recommended FlushDevice() pattern:

#include <exec/types.h>
#include <exec/execbase.h>
#include <exec/devices.h>
#include <proto/exec.h>

extern struct ExecBase *SysBase;

static int unload_device(const char *name)
{
    struct Device *device;

    Forbid();

    device = (struct Device *)
        FindName(&SysBase->DeviceList, (CONST_STRPTR)name);

    if (device != NULL)
        RemDevice(device);

    Permit();

    return device != NULL;
}

That pattern is almost verbatim what Commodore documents for deliberately flushing one named device.

The nice part is that your delayed-expunge logic already means this can behave correctly if a client still has fujinet-nio.device open:

RemDevice()
    -> device_expunge()
    -> OpenCnt != 0
    -> set LIBF_DELEXP
    -> return 0

later...

CloseDevice()
    -> OpenCnt becomes 0
    -> sees LIBF_DELEXP
    -> device_expunge()
    -> remove task/resources/device base
    -> return segment_list
    -> Exec unloads disk code

That is exactly the classic device lifecycle.

There is one significant issue in your disk device, though.

Your current fujinet-disk.device deliberately does not actually unload itself. Its device_expunge() says:

/* ... No unload. */
base->device.dd_Library.lib_Flags |= LIBF_DELEXP;
return complete_pending_expunge(base);

and complete_pending_expunge() shuts down transport state but ultimately:

return 0;

It does not Remove() the device node, free the device base/worker resources, or return its segment_list.

So at the moment:

RemDevice(fujinet-nio.device)

can genuinely unload the broker, provided nothing still holds it open.

But:

RemDevice(fujinet-disk.device)

currently means more like “request internal teardown/reset when idle”, not “remove the device binary from memory.”

That distinction matters because fujinet-disk.device is itself a client of the NIO broker. Your own architecture notes already identify that dependency: the disk device opens the broker through fn_transport_init() and needs to close it during disk-device teardown.

So for a full runtime reload of both devices, the order should be:

1. stop/dismount anything using fujinet-disk.device
2. RemDevice("fujinet-disk.device")
3. RemDevice("fujinet-nio.device")
4. load new fujinet-nio.device
5. load new fujinet-disk.device

But step 2 needs completing in your code first.

For fujinet-disk.device, I'd make complete_pending_expunge() eventually mirror the NIO device's real teardown:

segment_list = base->segment_list;

/* stop worker cleanly */
RemTask(&base->worker_task);
FreeMem(base->worker_stack, WORKER_STACK_SIZE);
FreeSignal(base->worker_signal);

/* close broker / transport */
fn_transport_close();

/* discard registrations/state */
discard_change_requests(base);

/* remove device node and base */
Forbid();
Remove((struct Node *)base);

FreeMem(
    (UBYTE *)base - base->device.dd_Library.lib_NegSize,
    (ULONG)base->device.dd_Library.lib_NegSize +
    (ULONG)base->device.dd_Library.lib_PosSize
);
Permit();

return segment_list;

with the same guards you already have for:

lib_OpenCnt == 0
queue empty
no request processing

I would also make the unload utility report whether removal actually happened. RemDevice() itself doesn't give you useful status, and once successful you mustn't dereference the old device pointer. The clean way is:

RemDevice(device);

Forbid();
device = (struct Device *)
    FindName(&SysBase->DeviceList, name);
Permit();

if (device == NULL)
    printf("%s unloaded\n", name);
else
    printf("%s still resident (probably open/busy)\n", name);

Do that as a fresh lookup, never by inspecting the original pointer after RemDevice().

For development, this would be very worthwhile. You could then FTP a new build and do:

fujinet-unload-resident fujinet-disk.device
fujinet-unload-resident fujinet-nio.device

fujinet-load-resident DEVS:fujinet-nio.device fujinet-nio.device
fujinet-load-resident DEVS:fujinet-disk.device fujinet-disk.device

instead of rebooting after every driver rebuild.

The only potentially awkward part is fujinet-disk.device: if DN filesystem handlers still have its units open, lib_OpenCnt won't reach zero, and that is exactly when unload should refuse/defer rather than force it. So the filesystem/DOS side has to be retired first; forcibly removing a live block device from underneath an active filesystem handler would be unsafe.

---

## Question 2
What would allow us to close the DN filesystem handlers? Typically I "mount" a drive via the command: fmount 0 DN0: RW which invokes 
fujinet-mount.c but there can be an fumount command (which we have on other platforms) to cleanly disconnect the same disk name from the amiga

## Answer 2
Yes — and your desired fumount command maps very naturally onto AmigaDOS’s handler lifecycle.

There are really two separate things to unmount:

the DOS filesystem handler for DN0:
the underlying FujiNet media mounted in fujinet-disk.device unit 0

Your existing fujinet-mount.c talks directly to fujinet-disk.device with OpenDevice()/DoIO(). It doesn’t currently manage the DOS handler lifecycle itself.

For a clean unload, I’d make fumount DN0: do this:

DN0: filesystem
   ↓
flush filesystem
   ↓
terminate filesystem handler
   ↓
eject FujiNet media
   ↓
CloseDevice()

The important AmigaDOS packet is ACTION_DIE. The RKM defines it specifically as “request the filesystem/handler to unmount its volumes and terminate.” A compliant handler should refuse if it still has active locks, file handles or notifications rather than disappearing unsafely.

So the basic implementation can use:

struct MsgPort *handler;

handler = DeviceProc("DN0:");

if (handler != NULL) {
    DoPkt(handler, ACTION_FLUSH, 0, 0, 0, 0, 0);
    result = DoPkt(handler, ACTION_DIE, 0, 0, 0, 0, 0);
}

ACTION_FLUSH is useful before shutdown because it tells the filesystem to push cached modifications down through the device layer.

There is an even better OS 3.2 route

Since your actual machine runs AmigaOS 3.2, it has the newer:

Dismount DN0:

command.

Unlike old:

Assign DN0: DISMOUNT

the OS 3.2 DISMOUNT command is explicitly intended to shut down the filesystem device and associated volumes. With no SOFT, the device is removed as though it had never been mounted.

So operationally, today you could test:

Dismount DN0:

and then inspect:

Status
Info

If the handler goes away and the open count on fujinet-disk.device falls, that is exactly the lifecycle we want.

However, because you care about OS 1.3 compatibility, I would not build fumount around the OS 3.2 command. Your own C implementation should use the classic packet APIs.

What fumount should probably mean

I’d give it a command line such as:

fumount DN0:

Internally it can derive:

DN0: -> unit 0
DN1: -> unit 1
...

Then:

1. Find the handler for DN0:
2. ACTION_FLUSH
3. ACTION_DIE
4. if ACTION_DIE fails:
       report "DN0: is busy"
       DO NOT eject the media
5. Send TD_EJECT / FUJINET_DISK_CMD_EJECT to unit 0
6. CloseDevice()

That failure ordering matters. You don't want:

open file on DN0:
        ↓
eject remote image
        ↓
filesystem still alive with stale blocks

Instead:

handler refuses ACTION_DIE
        ↓
fumount aborts
        ↓
disk remains mounted

which is much safer.

One subtlety: ACTION_DIE does not necessarily remove the DN0 DOS node

The RKM specifies that a terminating handler can set the relevant DOS-list dol_Task pointers to NULL. This leaves enough registration information for DOS potentially to restart the handler when someone accesses DN0: again.

That's useful for ordinary media ejection, but it's not enough if your eventual goal is unloading fujinet-disk.device itself, because an accidental:

Dir DN0:

could restart the filesystem and open the device again.

For your developer-oriented “unload all FujiNet drivers” workflow, I therefore see two levels:

fumount DN0:

Normal operation:

cleanly shut down DN0 handler
eject unit 0
perhaps leave DN0's DOS node available for later reuse

versus something like:

fumount DN0: REMOVE

Development/unload operation:

cleanly shut down handler
eject media
remove the DN0: DOS entry so it cannot respawn
then RemDevice(fujinet-disk.device)
then RemDevice(fujinet-nio.device)

On classic DOS, removing the registration would involve the DOS list (LockDosList() / FindDosEntry() / RemDosEntry()). Your previous project investigation also reached that same distinction: RemDosEntry() manipulates the DOS registration, whereas ACTION_DIE is what actually asks the handler to terminate.

I would not use Assign DN0: DISMOUNT as the implementation

That old command only removes the name from the DOS list; classic documentation explicitly says it does not free the resources.

So this:

Assign DN0: DISMOUNT

isn't sufficient for what you're building.

The proper abstraction for your driver suite is:

                     ┌──────────────┐
fmount 0 DN0: RW ───▶│ DOS handler  │
                     │     DN0:      │
                     └──────┬───────┘
                            │ OpenDevice
                     ┌──────▼──────────────┐
                     │ fujinet-disk.device │
                     │       unit 0        │
                     └──────┬──────────────┘
                            │
                     ┌──────▼─────────────┐
                     │ fujinet-nio.device │
                     └────────────────────┘


fumount DN0:
    ACTION_FLUSH
    ACTION_DIE
    TD_EJECT unit 0

Then a full development reload becomes:

fumount DN0:
fumount DN1:
...
fujinet-unload-resident fujinet-disk.device
fujinet-unload-resident fujinet-nio.device

And critically, if DN0: still has a Shell CDed into it, an open file, a Workbench drawer lock, DOpus lister, etc., fumount should report busy and stop, rather than forcibly killing anything. The RKM explicitly treats those outstanding locks/file handles as reasons ACTION_DIE may have to fail.

I think implementing fumount this way is the right next step before changing fujinet-disk.device's Expunge, because it gives you a deterministic way to drive its open count down to zero first.


