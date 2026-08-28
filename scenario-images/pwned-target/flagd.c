#include <stdio.h>

int main(void) {
    FILE *f = fopen("/root/flag-suid.txt", "r");
    char buf[256];
    if (!f) {
        puts("flag file missing");
        return 1;
    }
    while (fgets(buf, sizeof buf, f)) {
        fputs(buf, stdout);
    }
    fclose(f);
    return 0;
}