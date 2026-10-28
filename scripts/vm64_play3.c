/* vm64_play3.c  -- local speaker player for the Motorola VM64 (Anyka AK3918EV300)
 *
 * Build (on Jarvis with the matching cross toolchain):
 *   arm-anykav200-linux-uclibcgnueabi-gcc -O2 -o vm64_play3 vm64_play3.c -ldl -lpthread
 *
 * Usage:  vm64_play3 file(.wav/.pcm) [rate=8000] [param2=1] [vol=10]
 *   - Must run with fepe_simdev STOPPED (fepe holds /dev/akpcm_cdev0 exclusively -> EPERM).
 *   - RATE QUIRK: the DAC clocks at 2x the rate set, so for 16kHz content pass rate=8000.
 *   - ak_ao_set_volume() SIGFPEs on this chip rev and is intentionally NOT called;
 *     control loudness via the WAV sample amplitude instead.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

struct ao_param { unsigned int sample_rate; unsigned int param2; };

typedef void* (*fn_open)(struct ao_param*);
typedef int   (*fn_i_h)(void*);
typedef int   (*fn_i_hi)(void*, int);
typedef int   (*fn_send)(void*, void*, int);

/* libplat_ao.so relies on symbols the main app links globally; preload the providers. */
static const char* deps[] = {
    "/usr/lib/libplat_thread.so",
    "/usr/lib/libak_mt.so",
    "/usr/lib/libplat_common.so",
    "/usr/lib/libplat_drv.so",
    "/usr/lib/libakaudiocodec.so",
    "/usr/lib/libakaudiofilter.so",
    "/usr/lib/libplat_ipcsrv.so",
    "/usr/lib/libakmedia.so",
    0
};

int main(int argc, char** argv){
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc < 2){ fprintf(stderr,"usage: %s file(.wav/.pcm) [rate=8000] [param2=1] [vol=10]\n", argv[0]); return 2; }
    const char* fn = argv[1];
    int rate = argc>2 ? atoi(argv[2]) : 8000;
    int p2   = argc>3 ? atoi(argv[3]) : 1;
    int vol  = argc>4 ? atoi(argv[4]) : 10;

    FILE* f = fopen(fn,"rb");
    if(!f){ perror("fopen"); return 3; }
    fseek(f,0,SEEK_END); long sz = ftell(f); fseek(f,0,SEEK_SET);
    if(sz<=0){ fprintf(stderr,"empty file\n"); fclose(f); return 3; }
    unsigned char* data = (unsigned char*)malloc(sz);
    if(fread(data,1,sz,f)!=(size_t)sz){ fprintf(stderr,"read short\n"); }
    fclose(f);

    long off = 0;
    if(sz>44 && memcmp(data,"RIFF",4)==0){
        long i=12;
        while(i+8<=sz){
            unsigned int csz = data[i+4]|(data[i+5]<<8)|(data[i+6]<<16)|((unsigned)data[i+7]<<24);
            if(memcmp(data+i,"data",4)==0){ off=i+8; if(off+(long)csz<=sz) sz=off+csz; break; }
            i += 8 + csz + (csz&1);
        }
    }
    printf("file=%s total=%ld pcm_off=%ld pcm_bytes=%ld rate=%d param2=%d vol=%d\n",
           fn, sz, off, sz-off, rate, p2, vol);

    int i;
    for(i=0; deps[i]; i++){
        void* d = dlopen(deps[i], RTLD_LAZY|RTLD_GLOBAL);
        printf("dep %-32s %s\n", deps[i], d?"ok":"(skip)");
    }

    void* lib = dlopen("/usr/lib/libplat_ao.so", RTLD_LAZY|RTLD_GLOBAL);
    if(!lib){ fprintf(stderr,"dlopen libplat_ao: %s\n", dlerror()); free(data); return 5; }
    fn_open  ao_open   = (fn_open) dlsym(lib,"ak_ao_open");
    fn_i_hi  ao_sr     = (fn_i_hi) dlsym(lib,"ak_ao_set_sample_rate");
    fn_i_hi  ao_spk    = (fn_i_hi) dlsym(lib,"ak_ao_enable_speaker");
    fn_send  ao_send   = (fn_send) dlsym(lib,"ak_ao_send_frame");
    fn_i_h   ao_end    = (fn_i_h)  dlsym(lib,"ak_ao_notice_frame_end");
    fn_i_h   ao_close  = (fn_i_h)  dlsym(lib,"ak_ao_close");
    if(!ao_open||!ao_send||!ao_close){ fprintf(stderr,"dlsym missing core fn\n"); free(data); return 6; }

    struct ao_param pp; pp.sample_rate=rate; pp.param2=p2;
    void* h = ao_open(&pp);
    printf("ak_ao_open -> %p\n", h);
    if(!h){ fprintf(stderr,"open returned NULL\n"); free(data); return 7; }

    if(ao_sr)  printf("set_sample_rate(%d) -> %d\n", rate, ao_sr(h,rate));
    if(ao_spk) printf("enable_speaker(1)  -> %d\n", ao_spk(h,1));
    /* ak_ao_set_volume intentionally NOT called: SIGFPE on this chip rev. */

    long pos=off, total=0; int nsent=0;
    int chunk=1024;
    while(pos<sz){
        int n = (sz-pos)<chunk ? (int)(sz-pos) : chunk;
        int r = ao_send(h, data+pos, n);
        if(nsent<3) printf("send_frame(len=%d) -> %d\n", n, r);
        if(r<0){ printf("send_frame stop at %ld ret=%d\n", pos, r); break; }
        pos+=n; total+=n; nsent++;
    }
    printf("sent %ld bytes in %d frames\n", total, nsent);
    if(ao_end) printf("notice_frame_end -> %d\n", ao_end(h));
    usleep(500000);
    if(ao_close) printf("close -> %d\n", ao_close(h));
    free(data);
    printf("DONE\n");
    return 0;
}
