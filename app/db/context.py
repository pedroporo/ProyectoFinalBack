from contextvars import ContextVar

# Contexto para la base de datos del usuario
user_db_context = ContextVar('user_db', default=None)


def get_current_db():
    # print(f'Test get_current_db: {user_db_context.get().to_dict()}')
    return user_db_context.get()


def set_current_db(db):
    # print(f'Test db: {db.to_dict()}')
    # print(f'Test set_current_db: {user_db_context.set(db)}')
    user_db_context.set(db)
