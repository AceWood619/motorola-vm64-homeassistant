#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include "ak_global.h"
#include "ak_ao.h"

#define PCM_READ_BYTES 4096
#define DEFAULT_VOLUME 3

static void mono_to_stereo(const unsigned char *src, int bytes, unsigned char *dst)
{
    int i;
    for (i = 0; i + 1 < bytes; i += 2) {
        dst[i * 2] = src[i];
        dst[i * 2 + 1] = src[i + 1];
        dst[i * 2 + 2] = src[i];
        dst[i * 2 + 3] = src[i + 1];
    }
}

int main(int argc, char **argv)
{
    FILE *fp;
    struct pcm_param param;
    void *handle;
    unsigned char input[PCM_READ_BYTES];
    unsigned char output[PCM_READ_BYTES * 2];
    int n, sent, volume = DEFAULT_VOLUME, rc = 0, finished = 0;
    long total_bytes = 0, elapsed, timeout_ms;

    if (argc < 2 || argc > 3) {
        fprintf(stderr, "usage: %s <raw-8kHz-mono-s16le.pcm> [volume-0..6]\n", argv[0]);
        return 2;
    }
    if (argc == 3) volume = atoi(argv[2]);
    if (volume < 0 || volume > 6) {
        fprintf(stderr, "volume must be 0..6\n");
        return 2;
    }
    fp = fopen(argv[1], "rb");
    if (!fp) {
        fprintf(stderr, "cannot open PCM file: %s\n", strerror(errno));
        return 2;
    }

    memset(&param, 0, sizeof(param));
    param.sample_rate = 8000;
    param.sample_bits = 16;
    param.channel_num = AUDIO_CHANNEL_MONO;

    handle = ak_ao_open(&param);
    if (!handle) {
        fprintf(stderr, "ak_ao_open failed\n");
        fclose(fp);
        return 3;
    }

    if (ak_ao_enable_speaker(handle, AUDIO_FUNC_ENABLE) < 0) {
        fprintf(stderr, "speaker enable failed\n");
        rc = 4;
        goto cleanup;
    }
    if (ak_ao_set_dac_volume(handle, volume) < 0) {
        fprintf(stderr, "volume set failed\n");
        rc = 4;
        goto cleanup;
    }
    ak_ao_set_resample(handle, AUDIO_FUNC_DISABLE);
    ak_ao_clear_frame_buffer(handle);

    while ((n = (int)fread(input, 1, sizeof(input), fp)) > 0) {
        if (n & 1) {
            fprintf(stderr, "PCM byte count is not aligned to 16-bit samples\n");
            rc = 5;
            break;
        }
        mono_to_stereo(input, n, output);
        sent = ak_ao_send_frame(handle, output, n * 2, 0);
        if (sent < 0) {
            fprintf(stderr, "ak_ao_send_frame failed\n");
            rc = 6;
            break;
        }
        total_bytes += n;
        usleep(10000);
    }
    if (ferror(fp)) {
        fprintf(stderr, "PCM read failed\n");
        rc = 7;
    }
    fclose(fp);
    fp = NULL;

    ak_ao_notice_frame_end(handle);
    timeout_ms = (total_bytes / 16) + 5000;
    if (timeout_ms > 30000) timeout_ms = 30000;
    for (elapsed = 0; elapsed < timeout_ms; elapsed += 10) {
        if (ak_ao_get_play_status(handle) == AO_PLAY_STATUS_FINISHED) {
            finished = 1;
            break;
        }
        usleep(10000);
    }
    if (!finished)
        fprintf(stderr, "warning: playback status did not reach FINISHED before timeout\n");

cleanup:
    if (fp) fclose(fp);
    ak_ao_enable_speaker(handle, AUDIO_FUNC_DISABLE);
    ak_ao_close(handle);
    fprintf(stderr, "talkback_player: bytes=%ld volume=%d rc=%d finished=%d\n",
            total_bytes, volume, rc, finished);
    return rc;
}
