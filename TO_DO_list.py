task_list = list()

def show_menu():
    print("\n")
    print("------------THE COMMAND MENU------------")
    print("1. Add task")
    print("2. Remove a task")
    print("3. Print TO-DO list")
    print("4. Print Command menu")
def add_task():
    new_task = input("Enter a task: ")
    task_list.append(new_task)
def rm_task():
    del_task = input("Enter the task you want to remove exactly as you mentioned above: ")
    if del_task in task_list:
        task_list.remove(del_task)
    else:
        print("Task Not Found!!")

show_menu()
print("\n")

while True:
    operation = input("Enter option (1 or 2 or 3 or or 4 or QUIT): ")
    print('\n')
    if operation == "1" or operation == "2" or operation == "3" or operation == "4":
        if int(operation) == 1:
            add_task()
            print(task_list)
        elif int(operation) == 2 :
            rm_task()
            print(task_list)
        elif int(operation) == 3:
            if len(task_list) != 0:
                print("\n")
                print("________________TO DO LIST__________________")
                print(*task_list, sep = "\n")
                print("\n")
            else:
                print("Please add tasks first")
                print("\n")
        elif int(operation) == 4:
            print("------------THE COMMAND MENU------------")
            print("\n")
            print("1. Add task")
            print("2. Remove a task")
            print("3. Print TO-DO list")
            print("4. Print Command menu")

    elif operation == "QUIT" or operation == "quit" or operation == "Quit":
        break
    else:
        print("Invalid command, choose command from command menu:")
        print("1. Add task")
        print("2. Remove a task")
        print("3. Print TO-DO list")
        print("\n")
if len(task_list) != 0:
    print("________________TO DO LIST__________________")
    print("\n")
    print(*task_list, sep = "\n")
    print("\n")
    print("Thanks for using this Program")
else:
    print("No tasks found")
    print("\n")