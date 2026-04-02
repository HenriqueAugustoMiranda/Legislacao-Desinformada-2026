def get_sessionid():
    """Retorna o `sessionid` usado para autenticação no Instagram.

    Args:
        None.

    Returns:
        str: Token de sessão utilizado pelo cliente de coleta.
    """
    sessionid = '40783743325%3Ac2W5USzNo8kRPm%3A25%3AAYgX7RVi_3BlmEtdLGZlq8cpjrCsI4mIvLBWcrkcWw'  # sessionid da conta logada no Instagram
    return sessionid

def get_users():
    """Retorna a lista de perfis alvo para os scripts de coleta.

    Args:
        None.

    Returns:
        list[str]: Usuários do Instagram que serão processados.
    """
    users = ['popnewsjdr', 'sjddoficial', 'sjdr.prefeitura', 'sjddnews', 'ufsjbr']  # perfis alvo da coleta
    return users
