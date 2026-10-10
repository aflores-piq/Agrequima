/* =====================================================================
   PIQ_IA -- Campo Empresa en dbo.Usuarios (script 23)
   =====================================================================
   POR QUE: la bitacora de ingresos y el administrador de usuarios necesitan
   saber a que empresa pertenece cada usuario (texto libre, sin catalogo).

   QUE HACE:
     Agrega dbo.Usuarios.Empresa NVARCHAR(150) NULL (si no existe todavia).
     Los usuarios actuales quedan con Empresa = NULL (sin empresa) hasta que
     un administrador se la escriba desde la pantalla de Usuarios.

   Es seguro correrlo las veces que haga falta: solo agrega la columna si no
   existe y no borra ni modifica ningun dato.

   Consulta de ejemplo:
     SELECT UsuarioId, NombreUsuario, Empresa FROM dbo.Usuarios;
   ===================================================================== */

USE PIQ_IA;
GO


IF COL_LENGTH('dbo.Usuarios', 'Empresa') IS NULL
BEGIN
    ALTER TABLE dbo.Usuarios ADD Empresa NVARCHAR(150) NULL;
    PRINT 'Columna dbo.Usuarios.Empresa agregada.';
END
ELSE
    PRINT 'dbo.Usuarios.Empresa ya existia -- no se modifico nada.';
GO
