      PROGRAM FATORIAL
      INTEGER N, I, FAT
      PRINT *, 'Introduza um numero inteiro positivo:'
      READ *, N
      IF (N .LE. 0) THEN
      PRINT *, 'Numero invalido: deve ser positivo'
      ELSE
      FAT = 1
      DO 10 I = 1, N
      FAT = FAT * I
 10   CONTINUE
      PRINT *, 'Fatorial de ', N, ': ', FAT
      ENDIF
      END
