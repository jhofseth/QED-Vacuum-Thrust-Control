(kicad_sch
  (version 20231120) (generator "eeschema")

  (uuid 00000000-0000-0000-0000-000000000001)

  (paper "A3")

  (title_block
    (title "Basic Spherical Drone Prototype Schematic")
    (company "QED Project")
    (rev "1.0")
    (date "2025-11-01")
    (source "basic_drone.sch")
    (comment (number "1" (value "Low-power magnetic setup with neodymium magnets"))
    (comment (number "2" (value "Scalable to B_opposing >20T with electromagnets"))
    (comment (number "3" (value ""))
    (comment (number "4" (value ""))
  )

  (lib_symbols
    (symbol "MCU_Espressif:ESP32-DEVKITC" (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "ESP32-DEVKITC" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (property "Footprint" "" (at 0 0 0) (effects hide))
      (property "Datasheet" "" (at 0 0 0) (effects hide))
      (property "ki_keywords" "ESP32 WiFi Bluetooth" (at 0 0 0) (effects hide))
      (property "ki_description" "ESP32 Development Kit" (at 0 0 0) (effects hide))
      (pin "1" (uuid 00000000-0000-0000-0000-000000000002) (name "GPIO0" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      ; ... (abbreviated; in real file, all pins defined with graphics, etc.)
    )
    (symbol "Sensor:MPU-6050" (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "MPU-6050" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (pin "SCL" (uuid 00000000-0000-0000-0000-000000000003) (name "SCL" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin "SDA" (uuid 00000000-0000-0000-0000-000000000004) (name "SDA" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin "VCC" (uuid 00000000-0000-0000-0000-000000000005) (name "VCC" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin "GND" (uuid 00000000-0000-0000-0000-000000000006) (name "GND" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
      ; ... (abbreviated)
    )
    (symbol "Device:IRF540_MOSFET" (in_bom yes) (on_board yes)
      (property "Reference" "Q" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "IRF540" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (pin "G" (uuid 00000000-0000-0000-0000-000000000007) (name "Gate" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin "D" (uuid 00000000-0000-0000-0000-000000000008) (name "Drain" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin "S" (uuid 00000000-0000-0000-0000-000000000009) (name "Source" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      ; ... (abbreviated)
    )
    (symbol "Device:Coil" (in_bom yes) (on_board yes)
      (property "Reference" "L" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "Magnetic_Coil" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (pin "1" (uuid 00000000-0000-0000-0000-00000000000a) (name "In" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin "2" (uuid 00000000-0000-0000-0000-00000000000b) (name "Out" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      ; ... (abbreviated)
    )
    (symbol "Sensor:Hall_SS49E" (in_bom yes) (on_board yes)
      (property "Reference" "U" (at 0 0 0) (effects (font (size 1.27 1.27))))
      (property "Value" "SS49E" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
      (pin "OUT" (uuid 00000000-0000-0000-0000-00000000000c) (name "Out" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      ; ... (abbreviated)
    )
    (symbol "power:+3V3" (power) (pin power_in) (in_bom no) (on_board no)
      ; Abbreviated power symbol
    )
    (symbol "power:GND" (power) (pin power_in) (in_bom no) (on_board no)
      ; Abbreviated
    )
  )

  (junction (at 100.0 150.0) (diameter 0) (color 0 0 0 0) (uuid 00000000-0000-0000-0000-000000000010))

  (wire (pts (xy 50.0 100.0) (xy 100.0 100.0))
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000011)
  )

  (symbol (lib_id "MCU_Espressif:ESP32-DEVKITC") (at 50.0 100.0 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000012)
    (property "Reference" "U1" (at 50.0 105.0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "ESP32" (at 50.0 110.0 0) (effects (font (size 1.27 1.27))))
    (pin "GPIO21" (uuid 00000000-0000-0000-0000-000000000013))  ; PWM for MOSFET
    (pin "GPIO22" (uuid 00000000-0000-0000-0000-000000000014))  ; I2C SCL
    (pin "GPIO23" (uuid 00000000-0000-0000-0000-000000000015))  ; I2C SDA
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "U1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Sensor:MPU-6050") (at 150.0 100.0 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000016)
    (property "Reference" "U2" (at 150.0 105.0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "MPU-6050" (at 150.0 110.0 0) (effects (font (size 1.27 1.27))))
    (pin "SCL" (uuid 00000000-0000-0000-0000-000000000017))
    (pin "SDA" (uuid 00000000-0000-0000-0000-000000000018))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "U2") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Device:IRF540_MOSFET") (at 50.0 200.0 90) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000019)
    (property "Reference" "Q1" (at 50.0 205.0 90) (effects (font (size 1.27 1.27))))
    (property "Value" "IRF540" (at 50.0 210.0 90) (effects (font (size 1.27 1.27))))
    (pin "G" (uuid 00000000-0000-0000-0000-00000000001a))
    (pin "D" (uuid 00000000-0000-0000-0000-00000000001b))
    (pin "S" (uuid 00000000-0000-0000-0000-00000000001c))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "Q1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Device:Coil") (at 100.0 200.0 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid 00000000-0000-0000-0000-00000000001d)
    (property "Reference" "L1" (at 100.0 205.0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "Magnetic Coil" (at 100.0 210.0 0) (effects (font (size 1.27 1.27))))
    (pin "1" (uuid 00000000-0000-0000-0000-00000000001e))
    (pin "2" (uuid 00000000-0000-0000-0000-00000000001f))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "L1") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "Sensor:Hall_SS49E") (at 150.0 200.0 0) (unit 1)
    (in_bom yes) (on_board yes) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000020)
    (property "Reference" "U3" (at 150.0 205.0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "Hall Sensor" (at 150.0 210.0 0) (effects (font (size 1.27 1.27))))
    (pin "OUT" (uuid 00000000-0000-0000-0000-000000000021))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "U3") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "power:+3V3") (at 50.0 50.0 0) (unit 1)
    (in_bom no) (on_board no) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000022)
    (property "Reference" "#PWR01" (at 0 0 0) (effects hide))
    (property "Value" "+3V3" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "#PWR01") (unit 1)
        )
      )
    )
  )

  (symbol (lib_id "power:GND") (at 50.0 250.0 0) (unit 1)
    (in_bom no) (on_board no) (dnp no)
    (uuid 00000000-0000-0000-0000-000000000023)
    (property "Reference" "#PWR02" (at 0 0 0) (effects hide))
    (property "Value" "GND" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
    (instances
      (project "basic_drone"
        (path "/00000000-0000-0000-0000-000000000001"
          (reference "#PWR02") (unit 1)
        )
      )
    )
  )

  ; Connections - Example wires
  (wire (pts (xy 50.0 120.0) (xy 150.0 120.0))  ; I2C SCL from ESP32 GPIO22 to MPU SCL
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000024)
  )
  (wire (pts (xy 50.0 130.0) (xy 150.0 130.0))  ; I2C SDA
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000025)
  )
  (wire (pts (xy 50.0 140.0) (xy 50.0 190.0))  ; PWM from GPIO21 to MOSFET Gate
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000026)
  )
  (wire (pts (xy 60.0 200.0) (xy 90.0 200.0))  ; MOSFET Drain to Coil In
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000027)
  )
  (wire (pts (xy 110.0 200.0) (xy 140.0 200.0))  ; Coil Out to Hall or load
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000028)
  )
  (wire (pts (xy 50.0 60.0) (xy 50.0 90.0))  ; +3V3 to ESP32 VCC
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-000000000029)
  )
  (wire (pts (xy 40.0 200.0) (xy 40.0 240.0))  ; MOSFET Source to GND
    (stroke (width 0) (type default) (color 0 0 0 0))
    (uuid 00000000-0000-0000-0000-00000000002a)
  )

  (text "Note: Neodymium magnets integrated mechanically around coils for initial low-power B-field ( ~1.5T). For scaling to >20T, replace with high-field electromagnets (e.g., Hiperco-50 cores) and upgrade power supply." (at 200.0 250.0 0)
    (effects (font (size 1.27 1.27) italic))
    (uuid 00000000-0000-0000-0000-00000000002b)
  )

  (sheet_instances
    (path "/" (page "1"))
  )
)
