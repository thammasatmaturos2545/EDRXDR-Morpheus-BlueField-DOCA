#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include <doca_dev.h>
#include <doca_error.h>

int main(void)
{
    struct doca_devinfo **dev_list = NULL;
    uint32_t nb_devs = 0;

    doca_error_t result;

    printf("========================================\n");
    printf(" EDRXDR BlueField DOCA Device Probe\n");
    printf("========================================\n");

    /*
     * Ask DOCA for every local device it can access.
     */
    result = doca_devinfo_create_list(
        &dev_list,
        &nb_devs
    );

    if (result != DOCA_SUCCESS) {
        fprintf(
            stderr,
            "Failed to get DOCA devices: %s\n",
            doca_error_get_descr(result)
        );

        return 1;
    }

    printf("DOCA devices detected: %u\n\n", nb_devs);

    for (uint32_t i = 0; i < nb_devs; i++) {

        char ibdev_name[128] = {0};
        char iface_name[128] = {0};

        doca_error_t ib_result;
        doca_error_t iface_result;

        ib_result = doca_devinfo_get_ibdev_name(
            dev_list[i],
            ibdev_name,
            sizeof(ibdev_name)
        );

        iface_result = doca_devinfo_get_iface_name(
            dev_list[i],
            iface_name,
            sizeof(iface_name)
        );

        printf("Device #%u\n", i);

        if (ib_result == DOCA_SUCCESS) {
            printf("  IB device : %s\n", ibdev_name);
        } else {
            printf("  IB device : unavailable\n");
        }

        if (iface_result == DOCA_SUCCESS) {
            printf("  Interface : %s\n", iface_name);
        } else {
            printf("  Interface : unavailable\n");
        }

        printf("\n");
    }

    doca_devinfo_destroy_list(dev_list);

    printf("BlueField probe completed successfully.\n");

    return 0;
}
