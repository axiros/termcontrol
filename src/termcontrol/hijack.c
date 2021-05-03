#include <errno.h>
#include <fcntl.h>
#include <pty.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <termios.h>
#include <unistd.h>
#include <time.h>
/*
 * REFS:
 [1]: https://www.torsten-horn.de/techdocs/ascii.htm
 */


struct termios orig_termios;

// termcontrol globals:
int log_mode = 0;
int log_conv = 0;

int cmd_mode = 0;
int cmd_mode_before_pause = 0;
int cmd_mode_signal = 0;
int cmd_add_ctl = 0;
int cmd_add_alt = 0;
int cmd_add_128 = 0;
int cmd_to_upper = 0;
int key_insert_mode = 105; //i
int listen_jk = 0;
char *home_dir;

const size_t kBufSize = 1024;
time_t ts_last_j_key;


void set_jk_and_cmd_mode_based_on_flags() {
    if ( cmd_add_ctl || cmd_to_upper || cmd_add_alt || cmd_add_128 ) {
        listen_jk = 1;  
    } else {
        cmd_mode  = 0;
        listen_jk = 0;  
    }
}

void tty_restore() {
    fflush(STDIN_FILENO);
    tcsetattr(STDIN_FILENO, TCSANOW, &orig_termios);
}

void fatal(const char* str, ...) {
    int err = errno;
    va_list args;
    va_start(args, str);
    vfprintf(stderr, str, args);
    fprintf(stderr, "\n\terrno = %d\n\terror = %s\n", err, strerror(err));
    va_end(args);
    exit(-1);
}

void register_epoll(int epfd, int fd, int events) {
    struct epoll_event e;
    e.data.fd = fd;
    e.events = events;
    if (epoll_ctl(epfd, EPOLL_CTL_ADD, fd, &e)) {
        fatal("epoll_ctl failed");
    }
}

void write2(int fd, const char* buf, size_t len) {
    while (len > 0) {
        ssize_t count = write(fd, buf, len);
        if (count == -1) {
            fatal("write() failed");
        }
        len -= count;
        buf += count;
    }
}

void set_and_signal_cmd_mode(int cmdfd) {
    /* 
     * 1. switching the global var to cmd_mode
     * 2  sending alt-<signal> to the program
     * */
    cmd_mode = 1;
    if (cmd_mode_signal == 0) return;

    char buf[2];
    // ctrl-e -> fzf binds to that, changes prompt. Overwritable in environ:
    //buf[0] = to_cmd_mode;
    buf[0] = 27;
    buf[1] = cmd_mode_signal;
    write2(cmdfd, buf, 2);
}

void write_log(int log_type, int count, char* buf) {
    char *filename = "/termcontrol_input.log";
    char *filepath = malloc(strlen(home_dir) + strlen(filename) + 1);
    FILE * fp; // debug log
    int key;
    strncpy(filepath, home_dir, strlen(home_dir) + 1);
    strncat(filepath, filename, strlen(filename) + 1);
    fp = fopen(filepath,  "a+");
    fprintf(fp, "MUCA8[%d]: %d%d%d%d%d. ", log_type, cmd_mode, cmd_to_upper, cmd_add_ctl, cmd_add_alt, cmd_add_128);
    for (int i=0; i<count; i++) {
        key = buf[i];
        if (key < 0) key += 256; // we want to see 0-256
        fprintf(fp, "%d (0x%X). ", key, key);
    }
    fprintf(fp, "\n");
    fclose(fp);
}

void handle_cmd_mode(int cmdfd, int count, char *buf) {
    char cmdbuf[kBufSize]; // holds our translation
    int p = 0; // offset to buffer pos, when we insert alt modifier (27)
    int key;
    ts_last_j_key = 0; // just go sure it's reset. not in use in cmd mode

    for (int i=0; i<count; i ++) {
        key = buf[i];
        cmdbuf[i+p] = key;
        // 27's are followed by a letter key, we leave that next letter key:
        while (buf[i] == 27 && i<count) {
            i += 1;
            cmdbuf[i+p] = buf[i];
        }
        if (key > 31 && key < 128) {
            // i -> switch to insert mode:
            if (key == key_insert_mode) cmd_mode=0;

            if (cmd_to_upper == 1) {
                // a-z? all LETTERS to upper case:
                if (key >96 && key <123) cmdbuf[i+p] = key - 32;
            }

            if (cmd_add_ctl == 1) {
                // control sequences are ctrl-a=1, ctrl-b=2...:
                // a->ctrl-a and A->ctrl-a:
                if (key >96 && key <123) cmdbuf[i+p] = key - 96;
                if (key >64 && key <91)  cmdbuf[i+p] = key - 64;
            }

            if (cmd_add_alt == 1) {
                // alt works with *any* key, just prefixes with 27:
                cmdbuf[i+p] = 27;
                p += 1;
                cmdbuf[i+p] = key;
            }
        }
    }
    if (log_conv > 0) write_log(1, count+p, cmdbuf);
    write2(cmdfd, cmdbuf, count + p);
}

void handle_ins_mode(int cmdfd, int count, char *buf) {
    // we are in insert mode. codes: https://www.torsten-horn.de/techdocs/ascii.htm -> hit ctrl-a and see the 1 in the error log:
    // Note: this is keyboard, 'in' reads are handled via in_fd below.
    // count is Always 1
    // Try: hijack iodir /bin/sh

    // esacpe from insert mode: jk combo in stdin, usually in consecutive calls to this function:
    // j -> set?
    if ( listen_jk > 0) {
        // is jk within a count >1 buffer?
        if (count > 1) {
            int j=0;
            for (int i=0; i < count-1; i ++) {
                if (buf[i] == 106 && buf[i+1] == 107) {
                    cmd_mode = 1;
                    // flush all until the j
                    write2(cmdfd, buf, i); 
                    // flush all from the k:
                    for (j=0; j < count - i - 2; j++) buf[j] = buf[j+i+2];
                    count = j;
                }
            }
        } else if (buf[0] == 107 && ts_last_j_key > time(0)-2) {
            set_and_signal_cmd_mode(cmdfd);
            buf[0] = 8; // turn the k to backspace: i.e. delete the j, which was flushed before
        }
        // j typed at the end?
        if (buf[count-1] == 106) ts_last_j_key = time(0);
        else ts_last_j_key = 0; 
    }
    // insert mode write, unchanged normally, w/o jk :
    write2(cmdfd, buf, count);
}

int receiving_cmd = 0;
void handle_fifo_in_mode(int cmdfd, int count, char *buf) {
    // allow switch off insert mode from in writer as well:
    // printf '\x01\<cmd>' > in -> \01\240 (=\xf0) -> cmd mode on
    //write_log(count, buf);
    int i;
    int p=0; // offset (we don't forward control sequences intended for us)
    char appbuf[kBufSize]; // holds stuff for the app

    for (i=0; i<count; i++)  {
        if (receiving_cmd == 0) {
            if (buf[i] != 3) appbuf[i-p] = buf[i];
            else { receiving_cmd = 1; p +=1; }
        } else {
            p += 1;
            switch (buf[i] +256) {
                case 230: log_mode     = 1; break; 
                case 231: cmd_to_upper = 0; break;
                case 232: cmd_to_upper = 1; break;
                case 233: cmd_add_ctl  = 0; break;
                case 234: cmd_add_ctl  = 1; break;
                case 235: cmd_add_alt  = 0; break;
                case 236: cmd_add_alt  = 1; break;
                case 237: cmd_add_128  = 0; break;
                case 238: cmd_add_128  = 1; break;
                case 239: cmd_mode     = 0; break;
                case 240: cmd_mode     = 1; break; // silent setting, e.g. before signal consuming app starts
                case 241: set_and_signal_cmd_mode(cmdfd); break;
                          // pause
                case 242: {   
                              cmd_mode_before_pause=cmd_mode; 
                              cmd_mode = 0;
                              listen_jk = 0;
                              break;
                          }
                          // resume:
                case 243: cmd_mode = cmd_mode_before_pause; break;
                default: {
                             receiving_cmd = 0; 
                             p -= 1; 
                             i -= 1;
                             break;
                         }
            }
            if (buf[i] + 256 != 241) set_jk_and_cmd_mode_based_on_flags();
        }
    }

    //write_log(3, i-p, appbuf);
    write2(cmdfd, appbuf, i-p);
}



int handle(struct epoll_event* e, int cmdfd, int in_fd, int out_fd) {
    char buf[kBufSize];

    if (e->events & ~(EPOLLHUP | EPOLLIN)) {
        fatal("unexepected event %d on fd=%d", e->events, e->data.fd);
    }

    if (e->events & EPOLLIN) {
        ssize_t count = read(e->data.fd, buf, kBufSize);
        if (count == -1) fatal("bad read()");

        if (e->data.fd == STDIN_FILENO) {
            if (count > 0) {
                if (log_mode) write_log(0, count, buf);

                if (cmd_mode == 1) handle_cmd_mode(cmdfd, count, buf);
                else               handle_ins_mode(cmdfd, count, buf);

            }
        } else if (e->data.fd == cmdfd) {
            write2(STDOUT_FILENO, buf, count);
            write2(out_fd, buf, count);

        } else if (e->data.fd == in_fd) {

            handle_fifo_in_mode(cmdfd, count, buf);

        } else {
            fatal("unexpected fd for EPOLLIN event");
        }
    }

    if (e->events & EPOLLHUP) {
        if (e->data.fd == cmdfd) {
            exit(0);  // Eh?
        } else if (e->data.fd == in_fd) {
            return 1;
        } else {
            fatal("unexpected");
        }
    }
    return 0;
}

void init_tty() {
    if (tcgetattr(STDIN_FILENO, &orig_termios)) {
        fatal("tcgetattr failed");
    }

    if (atexit(tty_restore)) {
        fatal("couldn't call atexit");
    }

    struct termios raw = orig_termios;
    raw.c_iflag &= ~(BRKINT | ICRNL | INPCK | ISTRIP | IXON);
    raw.c_oflag &= ~(OPOST);
    raw.c_cflag |= (CS8);
    raw.c_lflag &= ~(ECHO | ICANON | IEXTEN | ISIG);
    // TODO: what of this voodoo is necessary?
    raw.c_cc[VMIN] = 5;
    raw.c_cc[VTIME] = 8;
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 0;
    raw.c_cc[VMIN] = 2;
    raw.c_cc[VTIME] = 0;
    raw.c_cc[VMIN] = 0;
    raw.c_cc[VTIME] = 8;

    if (tcsetattr(STDIN_FILENO, TCSAFLUSH, &raw)) {
        fatal("couldn't set terminal to raw mode");
    }
}

int init_epoll(int cmdfd) {
    int epfd = epoll_create(2);

    if (epfd == -1) {
        fatal("epoll_create failed");
    }

    register_epoll(epfd, STDIN_FILENO, EPOLLIN);
    register_epoll(epfd, cmdfd, EPOLLIN);
    return epfd;
}

void init_fs(char* dir, char** in_path, int* out_fd) {
    char* path = malloc(strlen(dir) + 5);

    sprintf(path, "%s/out", dir);
    *out_fd = open(path, O_CREAT | O_WRONLY | O_TRUNC, S_IRWXU);
    if (*out_fd == -1) {
        fatal("open() for out file failed");
    }

    sprintf(path, "%s/in", dir);
    if (unlink(path) && errno != ENOENT) {
        fatal("unlink()'ing in fifo failed");
    }

    *in_path = path;
}

int open_fifo(char* path, int epfd) {
    if (access(path, F_OK) == -1) {
        if (errno != ENOENT) {
            fatal("access() failed");
        }
        if (mkfifo(path, S_IRWXU)) {
            fatal("mkfifo() failed");
        }
    }
    int fd = open(path, O_RDONLY | O_NONBLOCK, 0);
    if (fd == -1) {
        fatal("open() on fifo failed");
    }

    register_epoll(epfd, fd, EPOLLIN);

    return fd;
}

void bridge(char* dir, int cmdfd) {
    int in_fd, out_fd;
    char* in_path;

    init_fs(dir, &in_path, &out_fd);
    init_tty();
    int epfd = init_epoll(cmdfd);
    in_fd = open_fifo(in_path, epfd);

    const size_t kMaxEvents = 64;
    struct epoll_event events[kMaxEvents];

    while (1) {
        int count = epoll_wait(epfd, events, kMaxEvents, -1);
        if (count == -1) {
            fatal("epoll_wait failed");
        }

        for (int i = 0; i < count; i++) {
            if (handle(&events[i], cmdfd, in_fd, out_fd)) {
                close(in_fd);
                in_fd = open_fifo(in_path, epfd);
            }
        }
    }

    free(in_path);
}

void exec_cmd(int fd, char** argv) {
    // so that the command (fzf) knows and can set bindings:
    setsid();
    dup2(fd, STDIN_FILENO);
    dup2(fd, STDOUT_FILENO);
    dup2(fd, STDERR_FILENO);
    if (ioctl(fd, TIOCSCTTY, NULL)) {
        fatal("failed to set the controlling terminal for the child process");
    }
    close(fd);
    execvp(argv[0], argv);
    fatal("execvp returned");
}

int shift(int argc, char** argv) {
    for (int c=1; c < argc; c++) argv[c] = argv[c+1];
    /* for (int i=0; i<argc; i++) printf("%s | ", argv[i]); */
    /* printf("\n"); */
    argv[argc] = NULL;
    return argc - 1;
}

int main(int argc, char** argv) {
    if (!isatty(STDIN_FILENO)) {
        fprintf(stderr, "You don't want to run this outside a tty...");
        exit(-1);
    }

    if (argc < 3) {
        fprintf(stderr, "\nUSAGE: hijack [SWITCHES] <dir> <cmd ...>\n");
        fprintf(stderr, "\nPurpose: \n");
        fprintf(stderr, "  - Hijackes tty stdin and stdout of the given cmd and makes their fds accessible via fifos in given directory.\n");
        fprintf(stderr, "  - Allows modifications of stdin in 'command mode', entered via jk, exitted via i by default.\n");
        fprintf(stderr, "\nSwitches: \n");
        fprintf(stderr, "  --cmd: set to command mode already at start (else via jk) [false]\n"     );
        fprintf(stderr, "  --cms <KEYCODE>: sig to send to app (as alt seq) when switching to command mode. 0 to send nothing. Ex: --cms 97 sends alt-a. [0]\n");
        fprintf(stderr, "  --ins <KEYCODE>: which key to enter for insert mode. Ex: --ins 63 for '?' [105] 'i']\n");
        fprintf(stderr, "  --ctl: in cmd mode, prefix any LETTER key with control key [false]\n");
        fprintf(stderr, "  --alt: in cmd mode, prefix ANY key with alt key [false]\n");
        fprintf(stderr, "  --upc: in cmd mode, uppercase any LETTER key [false]\n"   );
        fprintf(stderr, "  --128: in cmd mode, add 128 to any key [false]\n"         );
        fprintf(stderr, "  --log: log keys as typed into $HOME/termcontrol_input.log [false]\n");
        fprintf(stderr, "  --lgc: log keys as converted in cmd mode into $HOME/termcontrol_input.log [false]\n");
        fprintf(stderr, "\nPositional: \n");
        fprintf(stderr, "  dir: directory containing IO fifos. Those will persist after exit.\n");
        fprintf(stderr, "  cmd: program to run, with args\n");

        fprintf(stderr, "\nNotes:\n");
        fprintf(stderr, "  - Switches must come in this order (use the python wrapper for more convenience).\n");
        fprintf(stderr, "  - If nothing is set to modify stdin in command mode, than 'jk awareness' is skipped alltogether.\n");  
        fprintf(stderr, "  - Think twice about location of your io directory. Every user with read permissions on it can see what you type!\n");
        exit(-1);
    }
    //printf("%s %s %s %s %s!\n", argv[0], argv[1], argv[2], argv[3], argv[4]);
    home_dir = getenv("HOME");
    if (!strcmp("--cmd", argv[1])) {
        cmd_mode = 1;
        // you have to supply the 6 for ctrl-e (but could overwrite it):
        // to_cmd_mode = strtol(argv[2], &argv[2], 10); (if you want args parsing)
        argc = shift(argc, argv);
    }
    if (!strcmp("--cms", argv[1])) {
        cmd_mode_signal = strtol(argv[2], &argv[2], 10); 
        argc = shift(argc, argv);
        argc = shift(argc, argv);
    }
    if (!strcmp("--ins", argv[1])) {
        key_insert_mode = strtol(argv[2], &argv[2], 10); 
        argc = shift(argc, argv);
        argc = shift(argc, argv);
    }

    if (!strcmp("--ctl", argv[1])) {
        cmd_add_ctl = 1;
        argc = shift(argc, argv);
    }
    if (!strcmp("--alt", argv[1])) {
        cmd_add_alt = 1;
        argc = shift(argc, argv);
    }
    if (!strcmp("--upc", argv[1])) {
        cmd_to_upper = 1;
        argc = shift(argc, argv);
    }
    if (!strcmp("--128", argv[1])) {
        cmd_add_128 = 1;
        argc = shift(argc, argv);
    }
    if (!strcmp("--log", argv[1])) {
        log_mode = 1;
        argc = shift(argc, argv);
    }
    if (!strcmp("--lgc", argv[1])) {
        log_conv = 1;
        argc = shift(argc, argv);
    }

    set_jk_and_cmd_mode_based_on_flags();
    int m, s;

    struct winsize w;
    ioctl(STDOUT_FILENO, TIOCGWINSZ, &w);

    if (openpty(&m, &s, NULL, NULL, &w)) {
        fatal("openpty failed");
    }

    pid_t pid = fork();
    setenv("TERMCONTROL_IO_DIR",argv[1],1);                                      

    if (pid == -1) {
        fatal("fork failed");
    }

    if (pid == 0) {
        close(m);
        exec_cmd(s, argv + 2);
    } else {
        close(s);
        bridge(argv[1], m);
    }
}
