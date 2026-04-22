/**
 * @file he_api.h
 * @brief API for InnoPhase IoT He Ultra-Low-Power Wi-Fi SoC.
 */

/**
 * @defgroup he_wifi Wi-Fi Management
 * @brief Functions for managing Wi-Fi connectivity.
 * @{
 */

/**
 * @brief Initialize the Wi-Fi subsystem.
 * @return 0 on success, non-zero error code otherwise.
 */
int he_wifi_init(void);

/**
 * @brief Connect to a Wi-Fi access point.
 * @param ssid Service Set Identifier of the AP.
 * @param password Security key for the network.
 * @return 0 on connection success.
 */
int he_wifi_connect(const char* ssid, const char* password);

/**
 * @brief Get the current RSSI (Received Signal Strength Indicator).
 * @return Signal strength in dBm.
 */
float he_wifi_get_rssi(void);

/** @} */

/**
 * @defgroup he_power Power Management
 * @brief Functions for ultra-low-power optimization.
 * @{
 */

/**
 * @brief Set the sleep mode for the SoC.
 * @param mode 0 for Active, 1 for Light Sleep, 2 for Deep Sleep.
 */
void he_set_sleep_mode(int mode);

/** @} */
