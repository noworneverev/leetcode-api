HOME_PAGE_HTML ="""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>LeetCode API</title>
        <link rel="icon" type="image/png" href="https://img.icons8.com/material-rounded/48/000000/code.png">
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            /* Dark mode styles */
            body.dark-mode {
                background-color: #1a202c !important;
                color: #e2e8f0;
            }
            
            body.dark-mode .bg-white {
                background-color: #2d3748 !important;
            }

            body.dark-mode .text-gray-800 {
                color: #e2e8f0 !important;
            }

            body.dark-mode .text-gray-600 {
                color: #cbd5e0 !important;
            }

            body.dark-mode .text-gray-500 {
                color: #a0aec0 !important;
            }

            body.dark-mode .bg-blue-500 {
                background-color: #2563eb !important;
            }

            body.dark-mode .bg-green-500 {
                background-color: #059669 !important;
            }

            body.dark-mode .hover\:bg-blue-600:hover {
                background-color: #1d4ed8 !important;
            }

            body.dark-mode .hover\:bg-green-600:hover {
                background-color: #047857 !important;
            }
        </style>
    </head>
    <body class="bg-gray-100 min-h-screen flex items-center justify-center">
        <div class="max-w-2xl mx-4 text-center">
            <div class="bg-white rounded-lg shadow-lg p-8 space-y-6">
                <div class="flex justify-end space-x-2">
                    <!-- GitHub Icon Button -->
                    <a href="https://github.com/noworneverev/leetcode-api"
                    target="_blank"
                    class="flex items-center justify-center w-10 h-10 
                            rounded-full 
                            bg-gray-100 dark:bg-gray-700 
                            text-gray-600 dark:text-gray-300 
                            hover:bg-gray-200 dark:hover:bg-gray-600 
                            hover:text-gray-800 dark:hover:text-gray-100 
                            transition-colors duration-200 
                            focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        <i class="fab fa-github fa-lg"></i>
                    </a>

                    <!-- Theme Toggle Icon Button -->
                    <button id="theme-toggle"
                            class="flex items-center justify-center w-10 h-10 
                                rounded-full 
                                bg-gray-100 dark:bg-gray-700 
                                text-gray-600 dark:text-gray-300 
                                hover:bg-gray-200 dark:hover:bg-gray-600 
                                hover:text-gray-800 dark:hover:text-gray-100 
                                transition-colors duration-200 
                                focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                        <i id="theme-icon" class="fas fa-moon fa-lg"></i>
                    </button>
                </div>
                <h1 class="text-4xl font-bold text-gray-800 mb-4">
                    LeetCode API Gateway
                    <i class="fas fa-rocket text-blue-500 ml-2"></i>
                </h1>
                
                <p class="text-gray-600 text-lg">
                    Explore LeetCode data through our API endpoints. Get problem details,
                    user statistics, submissions history, and more!
                </p>

                <div class="flex flex-col sm:flex-row justify-center gap-4">
                    <a href="https://leetcode-api-pied.vercel.app/docs" 
                    target="_blank"
                    class="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg
                            transition-all duration-300 transform hover:scale-105
                            flex items-center justify-center gap-2">
                        <i class="fas fa-book-open"></i>
                        API Documentation
                    </a>
                    
                    <a href="https://docs.google.com/spreadsheets/d/1sRWp95wqo3a7lLBbtNd_3KkTyGjx_9sctTOL5JOb6pA/edit?usp=sharing" 
                    target="_blank"
                    class="bg-green-500 hover:bg-green-600 text-white px-6 py-3 rounded-lg
                            transition-all duration-300 transform hover:scale-105
                            flex items-center justify-center gap-2">
                        <i class="fas fa-table"></i>
                        Google Sheet (Updated Daily)
                    </a>
                </div>

                <p class="text-gray-500 text-sm mt-8 flex items-center justify-center gap-1">
        Made with ❤️ by 
        <a href="https://noworneverev.github.io/" target="_blank" 
        class="text-blue-500 font-semibold hover:text-blue-600 transition duration-300">
            Yan-Ying Liao
        </a>    
    </p>
            </div>
        </div>

        <script>
            const themeToggleBtn = document.getElementById('theme-toggle');
            const themeIcon = document.getElementById('theme-icon');
            const body = document.body;

            // Check local storage for theme preference
            const currentTheme = localStorage.getItem('theme');
            if (currentTheme === 'dark') {
                body.classList.add('dark-mode');
                themeIcon.classList.replace('fa-moon', 'fa-sun');
            }

            themeToggleBtn.addEventListener('click', () => {
                body.classList.toggle('dark-mode');
                if (body.classList.contains('dark-mode')) {
                    themeIcon.classList.replace('fa-moon', 'fa-sun');
                    localStorage.setItem('theme', 'dark');
                } else {
                    themeIcon.classList.replace('fa-sun', 'fa-moon');
                    localStorage.setItem('theme', 'light');
                }
            });
        </script>
    </body>
    </html>
    """