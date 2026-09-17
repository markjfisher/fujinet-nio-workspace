#define main directory_existing_test_main
#include "test_fujinet_nio_directory_backend.c"
#undef main
#include <sys/wait.h>

/* Synthetic independently scheduled peer; no real-service or guest claim. */
int main(void)
{
    int release[2], child_status;
    pid_t peer;
    uint8_t request[FN_HEADER_SIZE], response[32], detail, native;
    uint16_t length, status;
    unsigned first, reopened, second;
    make_temp_dir();
    write_identity();
    if (backend_open() != FN_OK || pipe(release) != 0) return 2;
    make_clock(request);
    peer = fork();
    if (peer < 0) return 2;
    if (peer == 0) {
        unsigned polls;
        char go;
        uint8_t old_reply[8] = {FN_DEVICE_CLOCK, FN_CMD_CLOCK_GET, 8, 0, 0, 1, 0, 0xa1};
        char tmp[300], final[300];
        close(release[1]);
        for (polls = 0; polls < 2000 && !file_exists_at(temp_dir, FN_DIRECTORY_TO_HOST_NAME); ++polls) usleep(1000);
        if (polls == 2000) _exit(3);
        remove_path(temp_dir, FN_DIRECTORY_TO_HOST_NAME);
        /* Request consumed, old result retained independently of mailboxes. */
        if (read(release[0], &go, 1) != 1) _exit(4);
        for (polls = 0; polls < 2000 && !file_exists_at(temp_dir, FN_DIRECTORY_TO_HOST_NAME); ++polls) usleep(1000);
        if (polls == 2000) _exit(5);
        seal(old_reply, sizeof(old_reply));
        if (write_file(temp_dir, "to-guest.pkt.tmp", old_reply, sizeof(old_reply)) != 0) _exit(6);
        snprintf(tmp, sizeof(tmp), "%s/to-guest.pkt.tmp", temp_dir);
        snprintf(final, sizeof(final), "%s/to-guest.pkt", temp_dir);
        if (rename(tmp, final) != 0) _exit(7);
        _exit(0);
    }
    close(release[0]);
    first = backend_exchange(request, sizeof(request), response, sizeof(response), &length, &detail, &native, &status);
    printf("first_result=%u first_length=%u\n", first, length);
    backend_close();
    reopened = backend_open();
    if (write(release[1], "x", 1) != 1) return 2;
    second = backend_exchange(request, sizeof(request), response, sizeof(response), &length, &detail, &native, &status);
    waitpid(peer, &child_status, 0);
    printf("reopen_result=%u second_result=%u second_length=%u stale_tag=%02x peer_exit=%d\n", reopened, second, length, length == 8 ? response[7] : 0, WIFEXITED(child_status) ? WEXITSTATUS(child_status) : -1);
    backend_close();
    rmdir_temp();
    /* Return success only when the unsafe behavior is reproduced. */
    return !(first == FN_ERR_TRANSPORT && reopened == FN_OK && second == FN_OK && length == 8 && response[7] == 0xa1 && WIFEXITED(child_status) && WEXITSTATUS(child_status) == 0);
}
