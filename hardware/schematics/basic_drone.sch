(kicad_sch
  (version 20231120)
  (generator "eeschema")
  (generator_version "8.0")

  (uuid "a1b2c3d4-e5f6-7890-abcd-ef1234567890")

  (paper "A3")

  (title_block
    (title "QED Vacuum Propulsion - Basic Spherical Drone Prototype")
    (date "2025-11-01")
    (rev "1.1")
    (company "QED Vacuum Thrust Control Project")
    (comment 1 "Low-power magnetic setup with neodymium magnets (~1.5T)")
    (comment 2 "Scalable to B_opposing >20T with high-field electromagnets")
    (comment 3 "ESP32 controller with IMU, Hall sensors, and PWM coil drivers")
    (comment 4 "Compatible with simulations/thrust_model.py")
  )

  (lib_symbols
    ;; ESP32 Development Board
    (symbol "MCU_Espressif:ESP32-DEVKITC"
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "ESP32-DEVKITC"
        (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "Module:ESP32-DEVKITC-32D"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32d_datasheet_en.pdf"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "ki_keywords" "ESP32 WiFi Bluetooth MCU"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "ki_description" "ESP32 Development Board with WiFi and Bluetooth"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "ESP32-DEVKITC_0_1"
        (rectangle
          (start -12.7 20.32)
          (end 12.7 -20.32)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "ESP32-DEVKITC_1_1"
        (pin power_in line (at -15.24 17.78 0) (length 2.54)
          (name "3V3" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin power_in line (at -15.24 15.24 0) (length 2.54)
          (name "GND" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 10.16 180) (length 2.54)
          (name "GPIO21/I2C_SDA" (effects (font (size 1.27 1.27))))
          (number "21" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 7.62 180) (length 2.54)
          (name "GPIO22/I2C_SCL" (effects (font (size 1.27 1.27))))
          (number "22" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 5.08 180) (length 2.54)
          (name "GPIO23/PWM" (effects (font (size 1.27 1.27))))
          (number "23" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 2.54 180) (length 2.54)
          (name "GPIO25/PWM" (effects (font (size 1.27 1.27))))
          (number "25" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 0 180) (length 2.54)
          (name "GPIO26/PWM" (effects (font (size 1.27 1.27))))
          (number "26" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 15.24 -2.54 180) (length 2.54)
          (name "GPIO27/PWM" (effects (font (size 1.27 1.27))))
          (number "27" (effects (font (size 1.27 1.27))))
        )
        (pin input line (at 15.24 -7.62 180) (length 2.54)
          (name "GPIO34/ADC" (effects (font (size 1.27 1.27))))
          (number "34" (effects (font (size 1.27 1.27))))
        )
        (pin input line (at 15.24 -10.16 180) (length 2.54)
          (name "GPIO35/ADC" (effects (font (size 1.27 1.27))))
          (number "35" (effects (font (size 1.27 1.27))))
        )
      )
    )

    ;; MPU-6050 IMU (6-axis accelerometer + gyroscope)
    (symbol "Sensor_Motion:MPU-6050"
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "MPU-6050"
        (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "Sensor_Motion:InvenSense_QFN-24_4x4mm_P0.5mm"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Datasheet" "https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "ki_keywords" "IMU accelerometer gyroscope I2C"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "MPU-6050_0_1"
        (rectangle
          (start -7.62 10.16)
          (end 7.62 -10.16)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "MPU-6050_1_1"
        (pin power_in line (at -10.16 7.62 0) (length 2.54)
          (name "VCC" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin power_in line (at -10.16 -7.62 0) (length 2.54)
          (name "GND" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 10.16 5.08 180) (length 2.54)
          (name "SCL" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
        (pin bidirectional line (at 10.16 2.54 180) (length 2.54)
          (name "SDA" (effects (font (size 1.27 1.27))))
          (number "4" (effects (font (size 1.27 1.27))))
        )
        (pin output line (at 10.16 -2.54 180) (length 2.54)
          (name "INT" (effects (font (size 1.27 1.27))))
          (number "5" (effects (font (size 1.27 1.27))))
        )
      )
    )

    ;; N-Channel MOSFET for PWM coil control
    (symbol "Transistor_FET:IRF540N"
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (pin_names (offset 0) hide)
      (property "Reference" "Q"
        (at 5.08 1.905 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Value" "IRF540N"
        (at 5.08 0 0)
        (effects (font (size 1.27 1.27)) (justify left))
      )
      (property "Footprint" "Package_TO_SOT_THT:TO-220-3_Vertical"
        (at 5.08 -1.905 0)
        (effects (font (size 1.27 1.27) italic) (justify left) hide)
      )
      (property "Datasheet" "http://www.irf.com/product-info/datasheets/data/irf540n.pdf"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) (justify left) hide)
      )
      (property "ki_keywords" "N-Channel MOSFET Power"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "IRF540N_0_1"
        (polyline
          (pts
            (xy 0.254 0)
            (xy -2.54 0)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline
          (pts
            (xy 0.254 1.905)
            (xy 0.254 -1.905)
          )
          (stroke (width 0.254) (type default))
          (fill (type none))
        )
        (polyline
          (pts
            (xy 2.54 -2.54)
            (xy 2.54 -1.27)
            (xy 0.254 -1.27)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline
          (pts
            (xy 2.54 2.54)
            (xy 2.54 1.27)
            (xy 0.254 1.27)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "IRF540N_1_1"
        (pin input line (at -5.08 0 0) (length 2.54)
          (name "G" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 2.54 5.08 270) (length 2.54)
          (name "D" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 2.54 -5.08 90) (length 2.54)
          (name "S" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
      )
    )

    ;; Magnetic Coil (Inductor)
    (symbol "Device:L"
      (pin_numbers hide)
      (pin_names (offset 0.254) hide)
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "L"
        (at 0 1.27 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Magnetic_Coil"
        (at 0 -1.27 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" ""
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "ki_keywords" "inductor coil reactor magnetic"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "L_0_1"
        (arc
          (start 0 -2.54)
          (mid 0.6323 -1.905)
          (end 0 -1.27)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (arc
          (start 0 -1.27)
          (mid 0.6323 -0.635)
          (end 0 0)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (arc
          (start 0 0)
          (mid 0.6323 0.635)
          (end 0 1.27)
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (arc
          (start 0 1.27)
          (mid 0.6323 1.905)
          (end 0 2.54)
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "L_1_1"
        (pin passive line (at 0 3.81 270) (length 1.27)
          (name "1" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin passive line (at 0 -3.81 90) (length 1.27)
          (name "2" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
      )
    )

    ;; Hall Effect Sensor
    (symbol "Sensor_Magnetic:A1301"
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "U"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Value" "Hall_Sensor_SS49E"
        (at 0 2.54 0)
        (effects (font (size 1.27 1.27)))
      )
      (property "Footprint" "Package_TO_SOT_THT:TO-92_Inline"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "ki_keywords" "hall effect magnetic sensor"
        (at 0 0 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (symbol "A1301_0_1"
        (rectangle
          (start -5.08 7.62)
          (end 5.08 -7.62)
          (stroke (width 0.254) (type default))
          (fill (type background))
        )
      )
      (symbol "A1301_1_1"
        (pin power_in line (at -7.62 5.08 0) (length 2.54)
          (name "VCC" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
        (pin power_in line (at -7.62 -5.08 0) (length 2.54)
          (name "GND" (effects (font (size 1.27 1.27))))
          (number "2" (effects (font (size 1.27 1.27))))
        )
        (pin output line (at 7.62 0 180) (length 2.54)
          (name "VOUT" (effects (font (size 1.27 1.27))))
          (number "3" (effects (font (size 1.27 1.27))))
        )
      )
    )

    ;; Power symbols
    (symbol "power:+3V3"
      (power)
      (pin_names (offset 0))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "#PWR"
        (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Value" "+3V3"
        (at 0 3.556 0)
        (effects (font (size 1.27 1.27)))
      )
      (symbol "+3V3_0_1"
        (polyline
          (pts
            (xy -0.762 1.27)
            (xy 0 2.54)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline
          (pts
            (xy 0 0)
            (xy 0 2.54)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
        (polyline
          (pts
            (xy 0 2.54)
            (xy 0.762 1.27)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "+3V3_1_1"
        (pin power_in line (at 0 0 90) (length 0) hide
          (name "+3V3" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
      )
    )

    (symbol "power:GND"
      (power)
      (pin_names (offset 0))
      (exclude_from_sim no)
      (in_bom yes)
      (on_board yes)
      (property "Reference" "#PWR"
        (at 0 -6.35 0)
        (effects (font (size 1.27 1.27)) hide)
      )
      (property "Value" "GND"
        (at 0 -3.81 0)
        (effects (font (size 1.27 1.27)))
      )
      (symbol "GND_0_1"
        (polyline
          (pts
            (xy 0 0)
            (xy 0 -1.27)
            (xy 1.27 -1.27)
            (xy 0 -2.54)
            (xy -1.27 -1.27)
            (xy 0 -1.27)
          )
          (stroke (width 0) (type default))
          (fill (type none))
        )
      )
      (symbol "GND_1_1"
        (pin power_in line (at 0 0 270) (length 0) hide
          (name "GND" (effects (font (size 1.27 1.27))))
          (number "1" (effects (font (size 1.27 1.27))))
        )
      )
    )
  )

  ;; Component instances
  (symbol (lib_id "MCU_Espressif:ESP32-DEVKITC") (at 80 100 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "12345678-1234-5678-1234-567812345678")
    (property "Reference" "U1" (at 80 120 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "ESP32-DEVKITC" (at 80 118 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "Module:ESP32-DEVKITC-32D" (at 80 100 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "" (at 80 100 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "U1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Sensor_Motion:MPU-6050") (at 160 80 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "23456789-2345-6789-2345-678923456789")
    (property "Reference" "U2" (at 160 92 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "MPU-6050" (at 160 90 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "" (at 160 80 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "U2") (unit 1)
        )
      )
    )
  )

  ;; MOSFET drivers for 4 coils (representative of 24-unit MADA array)
  (symbol (lib_id "Transistor_FET:IRF540N") (at 80 160 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "34567890-3456-7890-3456-789034567890")
    (property "Reference" "Q1" (at 85 161 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Value" "IRF540N" (at 85 159 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "Q1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Device:L") (at 110 150 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "45678901-4567-8901-4567-890145678901")
    (property "Reference" "L1" (at 112 150 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Value" "MADA_Coil_1" (at 112 148 0)
      (effects (font (size 1.27 1.27)) (justify left))
    )
    (property "Footprint" "" (at 110 150 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "L1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Sensor_Magnetic:A1301") (at 160 150 0) (unit 1)
    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)
    (uuid "56789012-5678-9012-5678-901256789012")
    (property "Reference" "U3" (at 160 160 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "Hall_SS49E" (at 160 158 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "U3") (unit 1)
        )
      )
    )
  )

  ;; Power symbols
  (symbol (lib_id "power:+3V3") (at 80 70 0) (unit 1)
    (exclude_from_sim no) (in_bom no) (on_board no) (dnp no)
    (uuid "67890123-6789-0123-6789-012367890123")
    (property "Reference" "#PWR01" (at 80 74 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Value" "+3V3" (at 80 66 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "#PWR01") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "power:GND") (at 80 180 0) (unit 1)
    (exclude_from_sim no) (in_bom no) (on_board no) (dnp no)
    (uuid "78901234-7890-1234-7890-123478901234")
    (property "Reference" "#PWR02" (at 80 186 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Value" "GND" (at 80 184 0)
      (effects (font (size 1.27 1.27)))
    )
    (instances
      (project "basic_drone"
        (path "/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
          (reference "#PWR02") (unit 1)
        )
      )
    )
  )

  ;; Wires and connections
  ;; Power connections
  (wire (pts (xy 80 70) (xy 80 82.36))
    (stroke (width 0) (type default))
    (uuid "89012345-8901-2345-8901-234589012345")
  )

  (wire (pts (xy 80 165.1) (xy 80 180))
    (stroke (width 0) (type default))
    (uuid "90123456-9012-3456-9012-345690123456")
  )

  ;; I2C connections: ESP32 to MPU-6050
  (wire (pts (xy 95.24 110.16) (xy 130 110.16))
    (stroke (width 0) (type default))
    (uuid "01234567-0123-4567-0123-456701234567")
  )
  (label "I2C_SCL" (at 110 110.16 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "11111111-1111-1111-1111-111111111111")
  )

  (wire (pts (xy 95.24 107.62) (xy 130 107.62))
    (stroke (width 0) (type default))
    (uuid "abcdef01-abcd-ef01-abcd-ef01abcdef01")
  )
  (label "I2C_SDA" (at 110 107.62 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "22222222-2222-2222-2222-222222222222")
  )

  ;; PWM to MOSFET gate
  (wire (pts (xy 95.24 105.08) (xy 75 105.08) (xy 75 160))
    (stroke (width 0) (type default))
    (uuid "bcdef012-bcde-f012-bcde-f012bcdef012")
  )
  (label "PWM_COIL1" (at 75 130 90) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "33333333-3333-3333-3333-333333333333")
  )

  ;; MOSFET drain to coil
  (wire (pts (xy 82.54 154.94) (xy 110 154.94) (xy 110 146.19))
    (stroke (width 0) (type default))
    (uuid "cdef0123-cdef-0123-cdef-0123cdef0123")
  )

  ;; Coil to ground
  (wire (pts (xy 110 153.81) (xy 110 170) (xy 80 170))
    (stroke (width 0) (type default))
    (uuid "def01234-def0-1234-def0-1234def01234")
  )

  ;; Hall sensor connections
  (wire (pts (xy 167.62 150) (xy 180 150))
    (stroke (width 0) (type default))
    (uuid "ef012345-ef01-2345-ef01-2345ef012345")
  )
  (label "HALL_OUT1" (at 175 150 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left bottom))
    (uuid "44444444-4444-4444-4444-444444444444")
  )

  (wire (pts (xy 180 150) (xy 180 130) (xy 95.24 130))
    (stroke (width 0) (type default))
    (uuid "f0123456-f012-3456-f012-3456f0123456")
  )

  ;; Hall sensor power
  (wire (pts (xy 152.38 145.08) (xy 140 145.08) (xy 140 70) (xy 80 70))
    (stroke (width 0) (type default))
    (uuid "fedcba98-fedc-ba98-fedc-ba98fedcba98")
  )

  (wire (pts (xy 152.38 155.08) (xy 140 155.08) (xy 140 170) (xy 80 170))
    (stroke (width 0) (type default))
    (uuid "edcba987-edcb-a987-edcb-a987edcba987")
  )

  ;; MPU-6050 power connections
  (wire (pts (xy 149.86 72.38) (xy 140 72.38) (xy 140 70))
    (stroke (width 0) (type default))
    (uuid "dcba9876-dcba-9876-dcba-9876dcba9876")
  )

  (wire (pts (xy 149.86 87.62) (xy 140 87.62) (xy 140 90) (xy 80 90))
    (stroke (width 0) (type default))
    (uuid "cba98765-cba9-8765-cba9-8765cba98765")
  )

  ;; MPU-6050 I2C connections
  (wire (pts (xy 170.16 85.08) (xy 180 85.08) (xy 180 110.16) (xy 130 110.16))
    (stroke (width 0) (type default))
    (uuid "ba987654-ba98-7654-ba98-7654ba987654")
  )

  (wire (pts (xy 170.16 82.54) (xy 185 82.54) (xy 185 107.62) (xy 130 107.62))
    (stroke (width 0) (type default))
    (uuid "a9876543-a987-6543-a987-6543a9876543")
  )

  ;; Text annotations
  (text "ESP32 Controller:\n- WiFi/BT for telemetry\n- I2C master for IMU\n- PWM outputs for coil drivers\n- ADC inputs for Hall sensors"
    (exclude_from_sim no)
    (at 40 50 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "55555555-5555-5555-5555-555555555555")
  )

  (text "MPU-6050 IMU:\n- 3-axis accelerometer\n- 3-axis gyroscope\n- I2C interface\n- Provides 6DOF data for Kalman filter"
    (exclude_from_sim no)
    (at 140 50 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "66666666-6666-6666-6666-666666666666")
  )

  (text "MADA Coil Array:\n- 24 units total (1 shown)\n- IRF540N MOSFET drivers\n- PWM: 50-100Hz (up to 1kHz bursts)\n- Neodymium magnets: ~1.5T\n- Scale to electromagnets for >20T"
    (exclude_from_sim no)
    (at 40 200 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "77777777-7777-7777-7777-777777777777")
  )

  (text "Hall Effect Sensors:\n- Monitor B-field strength\n- SS49E linear output\n- ADC input to ESP32\n- Real-time field measurement"
    (exclude_from_sim no)
    (at 140 200 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "88888888-8888-8888-8888-888888888888")
  )

  (text "Power System:\n- 3.3V for logic (ESP32, sensors)\n- 12-48V for coils (via MOSFETs)\n- Current monitoring recommended\n- Thermal management required"
    (exclude_from_sim no)
    (at 200 100 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "99999999-9999-9999-9999-999999999999")
  )

  (text "Integration Notes:\n\n1. This schematic shows 1 of 24 MADA units\n2. Replicate Q1-L1-U3 chain 24 times for full array\n3. Connect all to ESP32 PWM pins (use multiplexer if needed)\n4. Add current sensing (INA219) on each coil\n5. Add temperature sensors (DS18B20) for thermal monitoring\n6. Implement emergency shutdown circuitry\n7. Use hardware/interfaces.py for control\n8. Compatible with simulations/thrust_model.py\n\nSafety:\n- Magnetic shielding required\n- Current limiters on all coils\n- Thermal cutoff at 100°C\n- Emergency stop button\n\nScaling:\n- Low power: Neodymium magnets (~1.5T)\n- Mid power: Small electromagnets (5-10T)\n- High power: Hiperco-50 cores (20-60T)\n\nSee docs/bench_test_designs.md for experimental validation"
    (exclude_from_sim no)
    (at 40 250 0)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
  )

  ;; Global labels for multi-sheet designs
  (global_label "I2C_SCL" (shape input) (at 130 110.16 180) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify right))
    (uuid "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 130 110.16 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )

  (global_label "I2C_SDA" (shape input) (at 130 107.62 180) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify right))
    (uuid "cccccccc-cccc-cccc-cccc-cccccccccccc")
    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 130 107.62 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )

  (global_label "PWM_COIL1" (shape output) (at 95.24 105.08 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "dddddddd-dddd-dddd-dddd-dddddddddddd")
    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 95.24 105.08 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )

  (global_label "HALL_OUT1" (shape output) (at 180 150 0) (fields_autoplaced)
    (effects (font (size 1.27 1.27)) (justify left))
    (uuid "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
    (property "Intersheetrefs" "${INTERSHEET_REFS}" (at 180 150 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )

  ;; Sheet instances (for hierarchical designs)
  (sheet_instances
    (path "/" (page "1"))
  )
)
