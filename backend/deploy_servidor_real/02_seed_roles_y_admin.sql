/* =====================================================================
   PIQ_IA -- Roles y usuario administrador inicial
   =====================================================================
   Correr esto DESPUES de 01_crear_base_piq_ia.sql (necesita que las
   tablas Roles/Usuarios ya existan).

   Que hace:
     1. Inserta los 3 roles reales del sistema, con los MISMOS RolId
        que en la base de origen (1=Administrador, 2=Usuario,
        3=Administrador de Usuarios) -- importante para que coincidan
        si en algun momento se comparan/migran datos entre bases.
     2. Crea UN usuario administrador de produccion, con rol
        'Administrador', activo, con permiso de exportar.

   Antes de ejecutar el INSERT del usuario (parte 2, mas abajo), hay
   que completar 3 valores marcados con [PONÉ ACÁ ...] / [PEGÁ ACÁ ...]
   -- ver LEEME.txt, paso 2, para las instrucciones completas de como
   generar el valor de @PasswordHash (NUNCA escribir la contraseña en
   texto plano en este archivo -- se genera aparte con
   generar_hash_password.py, que no muestra ni guarda la contraseña en
   ningun lado, solo entrega el hash para pegar acá).

   Es seguro volver a correr este script mas de una vez: no duplica
   roles ni usuarios que ya existan.
   ===================================================================== */

USE PIQ_IA;
GO

/* ---------------------------------------------------------------------
   1. ROLES
   --------------------------------------------------------------------- */
SET IDENTITY_INSERT dbo.Roles ON;
GO

IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE RolId = 1)
    INSERT INTO dbo.Roles (RolId, NombreRol) VALUES (1, 'Administrador');

IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE RolId = 2)
    INSERT INTO dbo.Roles (RolId, NombreRol) VALUES (2, 'Usuario');

IF NOT EXISTS (SELECT 1 FROM dbo.Roles WHERE RolId = 3)
    INSERT INTO dbo.Roles (RolId, NombreRol) VALUES (3, 'Administrador de Usuarios');
GO

SET IDENTITY_INSERT dbo.Roles OFF;
GO

SELECT RolId, NombreRol FROM dbo.Roles ORDER BY RolId;
GO


/* ---------------------------------------------------------------------
   2. USUARIO ADMINISTRADOR DE PRODUCCIÓN
   --------------------------------------------------------------------- */

/* >>> COMPLETAR ESTOS 3 VALORES ANTES DE EJECUTAR ESTA SECCIÓN <<< */
DECLARE @NombreUsuario VARCHAR(100) = '[PONÉ ACÁ EL NOMBRE DE USUARIO PARA INICIAR SESIÓN, ej. admin]';
DECLARE @Email         VARCHAR(200) = '[PONÉ ACÁ TU CORREO PARA PRODUCCIÓN]';
DECLARE @PasswordHash  VARCHAR(255) = '[PEGÁ ACÁ EL HASH QUE TE DIO generar_hash_password.py]';
/* >>> ------------------------------------------------------------ <<< */

IF @NombreUsuario LIKE '[[]PONÉ%' OR @Email LIKE '[[]PONÉ%' OR @PasswordHash LIKE '[[]PEGÁ%'
BEGIN
    PRINT 'FALTA COMPLETAR LOS VALORES DE ARRIBA (@NombreUsuario / @Email / @PasswordHash) -- no se creó ningún usuario todavía.';
END
ELSE IF EXISTS (SELECT 1 FROM dbo.Usuarios WHERE NombreUsuario = @NombreUsuario)
BEGIN
    PRINT 'Ya existe un usuario con ese NombreUsuario -- no se creó nada, para no duplicar ni pisar la cuenta existente.';
END
ELSE
BEGIN
    INSERT INTO dbo.Usuarios (NombreUsuario, NombreCompleto, Email, PasswordHash, RolId, Activo, PuedeExportar)
    VALUES (@NombreUsuario, NULL, @Email, @PasswordHash, 1, 1, 1);
    PRINT 'Usuario administrador creado: ' + @NombreUsuario;
END
GO

SELECT UsuarioId, NombreUsuario, Email, RolId, Activo, PuedeExportar, FechaCreacion
FROM dbo.Usuarios
ORDER BY UsuarioId;
GO
