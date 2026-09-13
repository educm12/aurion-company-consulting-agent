-- =============================================================================
-- Base de datos: Aurion Consulting (empresa ficticia)
-- Propósito: Datos estructurados de empleados/departamentos/proyectos para
--            un agente de IA (LangChain + MCP) que combina esta información
--            con el manual de políticas indexado mediante RAG (ChromaDB).
-- Motor: SQLite 3
-- Fecha de referencia de los cálculos de antigüedad/edad: 2026-07-17
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- Limpieza (permite re-ejecutar el script sin duplicar datos)
-- -----------------------------------------------------------------------------
DROP TABLE IF EXISTS asignaciones_proyectos;
DROP TABLE IF EXISTS proyectos;
DROP TABLE IF EXISTS empleados;
DROP TABLE IF EXISTS departamentos;

-- -----------------------------------------------------------------------------
-- Tabla: departamentos
-- -----------------------------------------------------------------------------
CREATE TABLE departamentos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT NOT NULL UNIQUE,
    presupuesto       REAL NOT NULL,          -- presupuesto anual en EUR
    responsable       TEXT NOT NULL,          -- nombre completo del/de la responsable
    numero_empleados  INTEGER NOT NULL DEFAULT 0
);

-- -----------------------------------------------------------------------------
-- Tabla: empleados
-- -----------------------------------------------------------------------------
CREATE TABLE empleados (
    id                              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre                          TEXT NOT NULL,
    apellidos                       TEXT NOT NULL,
    departamento                    TEXT NOT NULL REFERENCES departamentos(nombre),
    puesto                          TEXT NOT NULL,
    salario                         REAL NOT NULL,             -- bruto anual en EUR
    fecha_contratacion              TEXT NOT NULL,              -- YYYY-MM-DD (antigüedad se calcula a partir de esta fecha)
    anios_experiencia               REAL NOT NULL,              -- experiencia profesional total (puede ser mayor que la antigüedad en la empresa)
    dias_vacaciones_disfrutados     INTEGER NOT NULL DEFAULT 0, -- disfrutados en el año en curso
    manager                         TEXT,                       -- nombre completo del/de la manager directo (NULL si es dirección)
    modalidad_trabajo               TEXT NOT NULL CHECK (modalidad_trabajo IN ('Presencial','Híbrido','Remoto')),
    ciudad                          TEXT NOT NULL,
    telefono                        TEXT NOT NULL,
    edad                            INTEGER NOT NULL,
    estado_civil                    TEXT NOT NULL,
    numero_hijos                    INTEGER NOT NULL DEFAULT 0,
    tiene_mascota                   INTEGER NOT NULL DEFAULT 0 CHECK (tiene_mascota IN (0,1)),
    tipo_mascota                    TEXT,                       -- NULL si tiene_mascota = 0
    rendimiento_anual               INTEGER NOT NULL CHECK (rendimiento_anual BETWEEN 1 AND 5), -- 1 = bajo, 5 = excelente
    bonus_anual                     REAL NOT NULL DEFAULT 0     -- EUR, según rendimiento
);

-- -----------------------------------------------------------------------------
-- Tabla: proyectos
-- -----------------------------------------------------------------------------
CREATE TABLE proyectos (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre            TEXT NOT NULL,
    cliente           TEXT NOT NULL,          -- 'Interno' si es un proyecto interno
    presupuesto       REAL NOT NULL,
    fecha_inicio      TEXT NOT NULL,
    fecha_fin         TEXT NOT NULL,
    estado            TEXT NOT NULL CHECK (estado IN ('Planificado','En curso','Finalizado','Pausado'))
);

-- -----------------------------------------------------------------------------
-- Tabla: asignaciones_proyectos (relación N:M entre empleados y proyectos)
-- -----------------------------------------------------------------------------
CREATE TABLE asignaciones_proyectos (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    empleado_id                 INTEGER NOT NULL REFERENCES empleados(id),
    proyecto_id                 INTEGER NOT NULL REFERENCES proyectos(id),
    rol_en_proyecto             TEXT NOT NULL,
    dedicacion_porcentaje       INTEGER NOT NULL CHECK (dedicacion_porcentaje BETWEEN 0 AND 100)
);

CREATE INDEX idx_empleados_departamento ON empleados(departamento);
CREATE INDEX idx_asignaciones_empleado ON asignaciones_proyectos(empleado_id);
CREATE INDEX idx_asignaciones_proyecto ON asignaciones_proyectos(proyecto_id);

-- -----------------------------------------------------------------------------
-- Datos: departamentos
-- -----------------------------------------------------------------------------
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Tecnología', 980000, 'Marta Iglesias Roldán', 7);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Comercial', 620000, 'Javier Ortega Beltrán', 5);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Recursos Humanos', 240000, 'Beatriz Salas Núñez', 3);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Marketing', 310000, 'Diego Ferrer Campos', 4);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Finanzas', 280000, 'Cristina Vidal Serrano', 3);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Operaciones', 350000, 'Ramón Cabrera Duque', 3);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Legal', 190000, 'Elena Prats Domínguez', 2);
INSERT INTO departamentos (nombre, presupuesto, responsable, numero_empleados) VALUES ('Atención al Cliente', 210000, 'Sergio Montoya Ríos', 3);

-- -----------------------------------------------------------------------------
-- Datos: empleados
-- -----------------------------------------------------------------------------
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Marta', 'Iglesias Roldán', 'Tecnología', 'Directora de Tecnología', 78500, '2015-03-02', 18, 22, NULL, 'Remoto', 'Madrid', '611203045', 44, 'Casada', 2, 1, 'Gato', 5, 9500);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Pablo', 'Nieto Serra', 'Tecnología', 'Arquitecto de Software', 62000, '2017-06-12', 14, 10, 'Marta Iglesias Roldán', 'Híbrido', 'Madrid', '622104456', 39, 'Casado', 1, 0, NULL, 4, 5200);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Lucía', 'Herrero Campos', 'Tecnología', 'Ingeniera de Datos Senior', 54000, '2019-01-15', 9, 14, 'Marta Iglesias Roldán', 'Remoto', 'Valencia', '633205567', 34, 'Soltera', 0, 1, 'Perro', 5, 4800);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Álvaro', 'Cano Molina', 'Tecnología', 'Desarrollador Backend', 41000, '2022-09-05', 5, 12, 'Marta Iglesias Roldán', 'Híbrido', 'Madrid', '644306678', 28, 'Soltero', 0, 0, NULL, 3, 1200);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Sara', 'Bermejo Vega', 'Tecnología', 'Desarrolladora Frontend', 39500, '2023-02-20', 4, 20, 'Marta Iglesias Roldán', 'Híbrido', 'Barcelona', '655407789', 27, 'Soltera', 0, 1, 'Gato', 4, 1500);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Iván', 'Cortés Aranda', 'Tecnología', 'Ingeniero DevOps', 47500, '2021-04-10', 8, 21, 'Marta Iglesias Roldán', 'Remoto', 'Málaga', '666508890', 33, 'Casado', 1, 0, NULL, 4, 2600);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Nuria', 'Esteban Cid', 'Tecnología', 'Analista QA', 34000, '2024-01-08', 3, 22, 'Marta Iglesias Roldán', 'Presencial', 'Madrid', '677609901', 25, 'Soltera', 0, 0, NULL, 3, 800);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Javier', 'Ortega Beltrán', 'Comercial', 'Director Comercial', 74000, '2014-05-19', 20, 12, NULL, 'Híbrido', 'Madrid', '699802123', 47, 'Casado', 3, 1, 'Perro', 5, 8800);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Patricia', 'Rincón Lozano', 'Comercial', 'Key Account Manager', 52000, '2018-03-11', 11, 17, 'Javier Ortega Beltrán', 'Híbrido', 'Madrid', '610903234', 38, 'Divorciada', 2, 0, NULL, 5, 4200);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Hugo', 'Santamaría Vidal', 'Comercial', 'Comercial Senior', 44000, '2020-07-01', 7, 10, 'Javier Ortega Beltrán', 'Presencial', 'Sevilla', '621004345', 35, 'Casado', 1, 0, NULL, 4, 3100);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Claudia', 'Gallego Moreno', 'Comercial', 'Comercial Junior', 29500, '2023-11-13', 2, 12, 'Javier Ortega Beltrán', 'Presencial', 'Madrid', '632105456', 26, 'Soltera', 0, 1, 'Perro', 3, 900);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Alba', 'Peña Carmona', 'Comercial', 'Responsable de Cuentas', 48000, '2019-09-23', 8, 18, 'Javier Ortega Beltrán', 'Híbrido', 'Madrid', '654307678', 36, 'Casada', 2, 0, NULL, 4, 3400);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Beatriz', 'Salas Núñez', 'Recursos Humanos', 'Directora de RRHH', 65000, '2016-02-08', 15, 11, NULL, 'Híbrido', 'Madrid', '665408789', 41, 'Casada', 2, 1, 'Gato', 5, 6200);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Óscar', 'Gil Fuentes', 'Recursos Humanos', 'Técnico de Selección', 33000, '2021-10-04', 6, 12, 'Beatriz Salas Núñez', 'Presencial', 'Madrid', '676509890', 30, 'Soltero', 0, 0, NULL, 4, 1600);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Irene', 'Marín Cuesta', 'Recursos Humanos', 'Técnica de Formación', 32500, '2022-01-17', 5, 18, 'Beatriz Salas Núñez', 'Híbrido', 'Madrid', '687600901', 29, 'Casada', 1, 1, 'Perro', 4, 1400);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Diego', 'Ferrer Campos', 'Marketing', 'Director de Marketing', 61000, '2017-11-20', 13, 19, NULL, 'Híbrido', 'Barcelona', '698701012', 40, 'Soltero', 0, 1, 'Gato', 4, 4800);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Carmen', 'Rey Ballesteros', 'Marketing', 'Especialista SEO/SEM', 37000, '2021-05-09', 6, 14, 'Diego Ferrer Campos', 'Remoto', 'Valencia', '609802123', 31, 'Soltera', 0, 0, NULL, 4, 1900);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Fernando', 'Aguirre León', 'Marketing', 'Diseñador Gráfico', 34500, '2020-08-14', 7, 20, 'Diego Ferrer Campos', 'Híbrido', 'Barcelona', '610903234', 33, 'Casado', 1, 0, NULL, 3, 1200);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Silvia', 'Quintana Osorio', 'Marketing', 'Community Manager', 30500, '2023-04-03', 3, 21, 'Diego Ferrer Campos', 'Remoto', 'Málaga', '621004345', 27, 'Soltera', 0, 1, 'Perro', 4, 1000);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Cristina', 'Vidal Serrano', 'Finanzas', 'Directora Financiera', 72000, '2013-09-16', 19, 11, NULL, 'Presencial', 'Madrid', '632105456', 46, 'Casada', 2, 0, NULL, 5, 7600);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Andrés', 'Lozano Miranda', 'Finanzas', 'Controller Financiero', 48500, '2018-12-01', 10, 23, 'Cristina Vidal Serrano', 'Híbrido', 'Madrid', '643206567', 37, 'Casado', 2, 0, NULL, 4, 3300);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Laura', 'Pastor Anaya', 'Finanzas', 'Analista Contable', 35000, '2022-03-28', 5, 19, 'Cristina Vidal Serrano', 'Presencial', 'Madrid', '654307678', 29, 'Soltera', 0, 1, 'Gato', 3, 1300);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Ramón', 'Cabrera Duque', 'Operaciones', 'Director de Operaciones', 68000, '2015-07-27', 17, 17, NULL, 'Presencial', 'Madrid', '665408789', 45, 'Casado', 3, 1, 'Perro', 4, 5900);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Yolanda', 'Domínguez Puente', 'Operaciones', 'Coordinadora Logística', 39000, '2019-10-10', 9, 12, 'Ramón Cabrera Duque', 'Presencial', 'Zaragoza', '676509890', 35, 'Divorciada', 1, 0, NULL, 4, 2400);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Tomás', 'Redondo Escobar', 'Operaciones', 'Técnico de Operaciones', 31000, '2023-06-06', 3, 23, 'Ramón Cabrera Duque', 'Presencial', 'Madrid', '687600901', 26, 'Soltero', 0, 0, NULL, 3, 900);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Elena', 'Prats Domínguez', 'Legal', 'Directora Legal', 70000, '2016-04-18', 16, 17, NULL, 'Híbrido', 'Madrid', '698701012', 43, 'Casada', 1, 0, NULL, 5, 6100);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Guillermo', 'Soler Manzano', 'Legal', 'Asesor Jurídico', 46000, '2020-02-24', 8, 11, 'Elena Prats Domínguez', 'Híbrido', 'Madrid', '609802123', 34, 'Soltero', 0, 1, 'Gato', 4, 2500);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Sergio', 'Montoya Ríos', 'Atención al Cliente', 'Director de Atención al Cliente', 58000, '2018-01-22', 12, 11, NULL, 'Presencial', 'Madrid', '610903234', 39, 'Casado', 2, 0, NULL, 4, 3900);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Marina', 'Rubio Contreras', 'Atención al Cliente', 'Agente de Soporte Senior', 32000, '2021-08-16', 6, 21, 'Sergio Montoya Ríos', 'Presencial', 'Sevilla', '621004345', 30, 'Soltera', 0, 1, 'Perro', 4, 1300);
INSERT INTO empleados (nombre, apellidos, departamento, puesto, salario, fecha_contratacion, anios_experiencia, dias_vacaciones_disfrutados, manager, modalidad_trabajo, ciudad, telefono, edad, estado_civil, numero_hijos, tiene_mascota, tipo_mascota, rendimiento_anual, bonus_anual) VALUES ('Adrián', 'Vega Palomo', 'Atención al Cliente', 'Agente de Soporte', 26500, '2024-03-11', 2, 18, 'Sergio Montoya Ríos', 'Presencial', 'Madrid', '632105456', 24, 'Soltero', 0, 0, NULL, 3, 500);

-- -----------------------------------------------------------------------------
-- Datos: proyectos
-- -----------------------------------------------------------------------------
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Migración Cloud Aurion', 'Interno', 180000, '2025-01-10', '2025-11-30', 'Finalizado');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Portal Cliente Nordic Bank', 'Nordic Bank', 320000, '2025-09-01', '2026-12-15', 'En curso');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('App Móvil RetailPlus', 'RetailPlus S.A.', 210000, '2026-02-15', '2026-10-31', 'En curso');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Rediseño Marca Aurion', 'Interno', 60000, '2026-04-01', '2026-08-31', 'En curso');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Auditoría Financiera Helios', 'Grupo Helios', 95000, '2026-06-01', '2026-09-30', 'En curso');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Plataforma Logística Zenit', 'Zenit Logistics', 275000, '2024-05-01', '2025-05-01', 'Finalizado');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('CRM Comercial 360', 'Interno', 130000, '2026-01-15', '2026-12-31', 'En curso');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Expansión Atención Cliente LatAm', 'Interno', 85000, '2026-09-01', '2027-03-31', 'Planificado');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Sistema Legal Compliance', 'Interno', 70000, '2025-03-01', '2025-12-20', 'Finalizado');
INSERT INTO proyectos (nombre, cliente, presupuesto, fecha_inicio, fecha_fin, estado) VALUES ('Optimización Cadena Suministro', 'Zenit Logistics', 150000, '2026-05-01', '2027-01-31', 'En curso');

-- -----------------------------------------------------------------------------
-- Datos: asignaciones_proyectos
-- -----------------------------------------------------------------------------
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (1, 1, 'Arquitecto', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (2, 1, 'Desarrollador', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (3, 1, 'Desarrollador', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (4, 1, 'DevOps', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (5, 1, 'QA', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (2, 2, 'Tech Lead', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (3, 2, 'Desarrollador', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (4, 2, 'Desarrollador', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (5, 2, 'DevOps', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (6, 2, 'QA', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (3, 3, 'Desarrollador', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (4, 3, 'Desarrollador', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (5, 3, 'Desarrollador', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (7, 3, 'QA', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (16, 4, 'Responsable', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (17, 4, 'Especialista', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (18, 4, 'Diseñador', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (19, 4, 'Community Manager', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (20, 5, 'Responsable', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (21, 5, 'Analista', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (22, 5, 'Analista', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (23, 6, 'Responsable', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (24, 6, 'Coordinador', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (25, 6, 'Técnico', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (4, 6, 'Soporte Técnico', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (8, 7, 'Responsable', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (9, 7, 'Comercial', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (10, 7, 'Comercial', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (11, 7, 'Comercial', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (12, 7, 'Comercial', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (3, 7, 'Comercial', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (28, 8, 'Responsable', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (29, 8, 'Agente', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (30, 8, 'Agente', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (26, 9, 'Responsable', 50);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (27, 9, 'Asesor', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (21, 9, 'Soporte', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (23, 10, 'Responsable', 100);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (24, 10, 'Coordinador', 75);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (25, 10, 'Técnico', 25);
INSERT INTO asignaciones_proyectos (empleado_id, proyecto_id, rol_en_proyecto, dedicacion_porcentaje) VALUES (8, 10, 'Consultor', 50);