import sqlite3

class Database:
    def __init__(self, path, root=False):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        
        self.cursor = self.connection.cursor()
        self.root = root
        
    def __del__(self):
        self.cursor.close()
        self.connection.close()
        
    def clear_all_tables(self) -> None:
        # confirm to really delete all data from all tables (cannot be restored)
        # ONLY WHEN NOT IN root mode which means self.root == False
        if not self.root:
            confirm = True if input(f"CAUTION: Clear all data from ALL tables? (y/n): ").lower() == "y" else False
            if not confirm:
                print("delete aborted.")
                return
        sql_fetch_tables = "SELECT name FROM sqlite_master WHERE type ='table';"
        self.cursor.execute(sql_fetch_tables)
        tables = [table[0] for table in self.cursor.fetchall()]
        
        print("deleted tables:", end="")
        for table in tables:
            self.cursor.execute(f"DELETE FROM {table}")
            self.connection.commit()
            print(f"{table}", end=", ")
                  
    def delete_all_rows(self, table) -> None:
        # confirm to really delete all rows (cannot be restored)
        # ONLY WHEN NOT IN root mode which means self.root == False
        if not self.root:
            confirm = True if input(f"CAUTION: Delete all rows from '{table}'? (y/n): ").lower() == "y" else False
            if not confirm:
                print("delete aborted.")
                return
                
        # proceed to delete all rows
        sql = f"DELETE FROM {table};"
        self.cursor.execute(sql)
        self.connection.commit()
        print(f"deleted all rows from {table}")
        
    def stringify(self, text, preserve_int=False):
        """
        preserve int is an optional argument to dump any value in stringify
        and no cases need to be considered beforehand
        ... so int values dont get put in quotes
        """
        
        # clean non-strings
        if type(text) != str:
            if preserve_int == True:
                return str(text)
            else:            
                try:
                    return str(text)
                except:
                    print(text, "cannot be converted to string.")
                    return
        # clean strings
        text = text.replace("'", "''") # excape single quotes in text
        text = f"'{text}'"             # add single quotes to mark string
        return text        
        
    def insert_row(self, table, row: dict) -> None:
        '''insert row in table if not exists. row provided as dict with {"col1" : val1, "col2" : val2}'''
        # sql command string
        sql = f"""
        insert into {table} ({','.join([column for column in row])})
        values ( {','.join([self.stringify(value, preserve_int=True) for value in row.values()])} );
        """
        # exceute command
        try:
            self.cursor.execute(sql)
            self.connection.commit()
        except sqlite3.IntegrityError:
            # print("row or primary key already exist")
            pass
        except sqlite3.OperationalError as e:
            print("[Operational Error]", e)
            quit()
        except Exception as e:
            print("ERROR:", e)
            
    def update_cell(self, table, column, primary_keys: dict, new_value) -> None:
        '''
        update at specific cell,
        specified by column and (multiple) primary keys
        '''
        # specify rows by primary key(s). (where condition)
        condition = ' and '.join([
            f'{row} = {self.stringify(value)}'
            for row, value in primary_keys.items()
        ])
        
        sql = f"""
        update {table}
        set {column} = {self.stringify(new_value, preserve_int=True)}
        where {condition};
        """
        try:
            self.cursor.execute(sql)
            self.connection.commit()  
        except Exception as e:
            print("ERROR:", e)
        
    def get_all(self, sql_query) -> dict:
        """
        fetch all rows of sql query
        :param sql_query: string that contains query
        :return: dict with rows
        """
        self.cursor.execute(sql_query)
        json = [ dict(row) for row in self.cursor.fetchall() ]
        return json

if __name__ == "__main__":
    pass