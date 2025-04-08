
import flet as ft

class Module:
    def get_module_info(self):
        return {
            "name": "Calculadora",
            "description": "Uma calculadora simples",
            "version": "1.0.0",
            "icon": ft.icons.CALCULATE,
            "color": ft.colors.GREEN,
        }
        
    def get_view(self):
        self.result = ft.Text("0", size=32, text_align=ft.TextAlign.RIGHT)
        
        def button_clicked(e):
            data = e.control.data
            
            if data == "C":
                self.result.value = "0"
            elif data == "=":
                try:
                    self.result.value = str(eval(self.result.value))
                except:
                    self.result.value = "Erro"
            else:
                if self.result.value == "0" or self.result.value == "Erro":
                    self.result.value = data
                else:
                    self.result.value += data
                    
            e.page.update()
        
        buttons = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["C", "0", "=", "+"]
        ]
        
        button_rows = []
        for row in buttons:
            button_row = []
            for button in row:
                btn = ft.ElevatedButton(
                    text=button,
                    data=button,
                    width=60,
                    height=60,
                    on_click=button_clicked,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                button_row.append(btn)
            button_rows.append(ft.Row(button_row, alignment=ft.MainAxisAlignment.CENTER))
        
        return ft.Column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Calculadora", size=24, weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=self.result,
                                bgcolor=ft.colors.BLACK12,
                                border_radius=10,
                                padding=10,
                                width=280,
                                height=60,
                                alignment=ft.alignment.center_right,
                            ),
                            ft.Container(height=20),
                            *button_rows
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=20,
                    border_radius=10,
                    bgcolor=ft.colors.SURFACE,
                    width=320,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
