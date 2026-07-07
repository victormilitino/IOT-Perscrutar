import shutil
import os
from database import Database

def main():
    db = Database()
    people = db.load()
    if not people:
        print('Nenhuma pessoa cadastrada em data.json.')
        return
    while True:
        people = db.load()
        if not people:
            print('\nTodos os cadastros foram removidos.')
            break
        print('\n=== CADASTROS ATUAIS ===')
        for i, p in enumerate(people):
            print(f'[{i}] Nome: {p.name} | Tag: {p.tag} | ID: {p.id} | Fotos: {p.image_path}')
        escolha = input("\nDigite o número da pessoa para APAGAR, 'todos' para apagar tudo, ou ENTER para sair: ").strip()
        if escolha == '':
            break
        if escolha.lower() == 'todos':
            confirmacao = input('Tem certeza? Isso apaga TODOS os cadastros e fotos (sim/nao): ')
            if confirmacao.lower() == 'sim':
                for p in people:
                    if os.path.isdir(p.image_path):
                        shutil.rmtree(p.image_path, ignore_errors=True)
                db.save([])
                print('Todos os cadastros foram apagados.')
            continue
        if not escolha.isdigit() or int(escolha) not in range(len(people)):
            print('Opção inválida.')
            continue
        index = int(escolha)
        pessoa_remover = people[index]
        confirmacao = input(f"Apagar '{pessoa_remover.name}'? (sim/nao): ")
        if confirmacao.lower() != 'sim':
            continue
        if os.path.isdir(pessoa_remover.image_path):
            shutil.rmtree(pessoa_remover.image_path, ignore_errors=True)
        elif os.path.isfile(pessoa_remover.image_path):
            os.remove(pessoa_remover.image_path)
        people_restantes = [p for p in people if p.id != pessoa_remover.id]
        db.save(people_restantes)
        print(f"'{pessoa_remover.name}' removido com sucesso.")
if __name__ == '__main__':
    main()