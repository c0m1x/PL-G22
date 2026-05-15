      PROGRAM PRIMO
      INTEGER NUM, I
      LOGICAL ISPRIM
      PRINT *, 'Introduza um numero inteiro positivo:'
      READ *, NUM
      IF (NUM .LE. 0) THEN
      PRINT *, 'Numero invalido: deve ser positivo'
      ELSE
      ISPRIM = .TRUE.
      I = 2
      IF (NUM .EQ. 1) THEN
      ISPRIM = .FALSE.
      ELSE
 20   IF (I .LE. (NUM/2) .AND. ISPRIM) THEN
      IF (MOD(NUM, I) .EQ. 0) THEN
      ISPRIM = .FALSE.
      ENDIF
      I = I + 1
      GOTO 20
      ENDIF
      ENDIF
      IF (ISPRIM) THEN
      PRINT *, NUM, ' e um numero primo'
      ELSE
      PRINT *, NUM, ' nao e um numero primo'
      ENDIF
      ENDIF
      END
