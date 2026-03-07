"""
Dictionnaire des traductions pour le système de bulletin scolaire
Utilisation : t('cle', langue) où langue est 'fr' ou 'ar'
"""

TRANSLATIONS = {
    # Navigation et menu
    'dashboard': {'fr': 'Tableau de bord', 'ar': 'لوحة التحكم'},
    'logout': {'fr': 'Déconnexion', 'ar': 'تسجيل الخروج'},
    'login': {'fr': 'Connexion', 'ar': 'تسجيل الدخول'},
    'back': {'fr': 'Retour', 'ar': 'العودة'},
    
    # Gestion des classes
    'classes': {'fr': 'Classes', 'ar': 'الفصول'},
    'add_class': {'fr': 'Ajouter une classe', 'ar': 'إضافة فصل'},
    'manage_classes': {'fr': 'Gérer les classes', 'ar': 'إدارة الفصول'},
    'class_name': {'fr': 'Nom de la classe', 'ar': 'اسم الفصل'},
    'academic_year': {'fr': 'Année scolaire', 'ar': 'السنة الدراسية'},
    'existing_classes': {'fr': 'Classes existantes', 'ar': 'الفصول الموجودة'},
    
    # Gestion des élèves
    'students': {'fr': 'Élèves', 'ar': 'الطلاب'},
    'add_student': {'fr': 'Ajouter un élève', 'ar': 'إضافة طالب'},
    'manage_students': {'fr': 'Gérer élèves', 'ar': 'إدارة الطلاب'},
    'first_name': {'fr': 'Prénom', 'ar': 'الاسم الأول'},
    'last_name': {'fr': 'Nom', 'ar': 'اسم العائلة'},
    'birth_date': {'fr': 'Date de naissance', 'ar': 'تاريخ الميلاد'},
    'gender': {'fr': 'Sexe', 'ar': 'الجنس'},
    'male': {'fr': 'Masculin', 'ar': 'ذكر'},
    'female': {'fr': 'Féminin', 'ar': 'أنثى'},
    'guardian': {'fr': 'Tuteur', 'ar': 'ولي الأمر'},
    'guardian_phone': {'fr': 'Téléphone du tuteur', 'ar': 'هاتف ولي الأمر'},
    
    # Gestion des matières
    'subjects': {'fr': 'Matières', 'ar': 'المواد'},
    'add_subject': {'fr': 'Ajouter une matière', 'ar': 'إضافة مادة'},
    'manage_subjects': {'fr': 'Gérer matières', 'ar': 'إدارة المواد'},
    'subject_name': {'fr': 'Nom de la matière', 'ar': 'اسم المادة'},
    'teacher': {'fr': 'Professeur', 'ar': 'المدرس'},
    'day': {'fr': 'Jour', 'ar': 'اليوم'},
    'time': {'fr': 'Heure', 'ar': 'الوقت'},
    'duration': {'fr': 'Durée', 'ar': 'المدة'},
    
    # Gestion des notes
    'grades': {'fr': 'Notes', 'ar': 'الدرجات'},
    'enter_grades': {'fr': 'Saisir notes', 'ar': 'إدخال الدرجات'},
    'manage_grades': {'fr': 'Gérer les notes', 'ar': 'إدارة الدرجات'},
    'grade': {'fr': 'Note', 'ar': 'الدرجة'},
    'trimester': {'fr': 'Trimestre', 'ar': 'الفصل الدراسي'},
    'trimester_1': {'fr': 'Premier Trimestre', 'ar': 'الفصل الأول'},
    'trimester_2': {'fr': 'Deuxième Trimestre', 'ar': 'الفصل الثاني'},
    'trimester_3': {'fr': 'Troisième Trimestre', 'ar': 'الفصل الثالث'},
    'average': {'fr': 'Moyenne', 'ar': 'المعدل'},
    'general_average': {'fr': 'Moyenne générale', 'ar': 'المعدل العام'},
    
    # Bulletin et évaluations
    'report_card': {'fr': 'Bulletin scolaire', 'ar': 'بطاقة التقرير المدرسي'},
    'annual_report': {'fr': 'Bulletin scolaire annuel', 'ar': 'التقرير المدرسي السنوي'},
    'reports': {'fr': 'Bulletins', 'ar': 'التقارير'},
    'print_reports': {'fr': 'Imprimer tous', 'ar': 'طباعة الكل'},
    'download_pdf': {'fr': 'Télécharger PDF', 'ar': 'تحميل ملف PDF'},
    'preview': {'fr': 'Prévisualisation', 'ar': 'معاينة'},
    'ranking': {'fr': 'Classement', 'ar': 'الترتيب'},
    'appreciation': {'fr': 'Appréciation', 'ar': 'التقدير'},
    
    # Mentions et appréciations
    'excellent': {'fr': 'Excellent', 'ar': 'ممتاز'},
    'very_good': {'fr': 'Très bien', 'ar': 'جيد جداً'},
    'good': {'fr': 'Bien', 'ar': 'جيد'},
    'fairly_good': {'fr': 'Assez bien', 'ar': 'مقبول جداً'},
    'passable': {'fr': 'Passable', 'ar': 'مقبول'},
    'insufficient': {'fr': 'Insuffisant', 'ar': 'غير كافي'},
    
    # Actions générales
    'save': {'fr': 'Enregistrer', 'ar': 'حفظ'},
    'edit': {'fr': 'Modifier', 'ar': 'تعديل'},
    'delete': {'fr': 'Supprimer', 'ar': 'حذف'},
    'cancel': {'fr': 'Annuler', 'ar': 'إلغاء'},
    'confirm': {'fr': 'Confirmer', 'ar': 'تأكيد'},
    'add': {'fr': 'Ajouter', 'ar': 'إضافة'},
    'view': {'fr': 'Voir', 'ar': 'عرض'},
    'print': {'fr': 'Imprimer', 'ar': 'طباعة'},
    
    # Messages et statuts
    'no_students': {'fr': 'Aucun élève inscrit', 'ar': 'لا يوجد طلاب مسجلون'},
    'no_subjects': {'fr': 'Aucune matière configurée', 'ar': 'لا توجد مواد مكونة'},
    'no_classes': {'fr': 'Aucune classe créée', 'ar': 'لا توجد فصول مُنشأة'},
    'ready_for_grades': {'fr': 'Prête pour les notes', 'ar': 'جاهز للدرجات'},
    'incomplete_setup': {'fr': 'Configuration incomplète', 'ar': 'الإعداد غير مكتمل'},
    'success': {'fr': 'Succès', 'ar': 'نجح'},
    'error': {'fr': 'Erreur', 'ar': 'خطأ'},
    'warning': {'fr': 'Avertissement', 'ar': 'تحذير'},
    
    # Informations école
    'school': {'fr': 'École', 'ar': 'المدرسة'},
    'director': {'fr': 'Directeur', 'ar': 'المدير'},
    'address': {'fr': 'Adresse', 'ar': 'العنوان'},
    'phone': {'fr': 'Téléphone', 'ar': 'الهاتف'},
    'email': {'fr': 'Email', 'ar': 'البريد الإلكتروني'},
    
    # Jours de la semaine
    'monday': {'fr': 'Lundi', 'ar': 'الاثنين'},
    'tuesday': {'fr': 'Mardi', 'ar': 'الثلاثاء'},
    'wednesday': {'fr': 'Mercredi', 'ar': 'الأربعاء'},
    'thursday': {'fr': 'Jeudi', 'ar': 'الخميس'},
    'friday': {'fr': 'Vendredi', 'ar': 'الجمعة'},
    'saturday': {'fr': 'Samedi', 'ar': 'السبت'},
    'sunday': {'fr': 'Dimanche', 'ar': 'الأحد'},
    
    # Statistiques
    'statistics': {'fr': 'Statistiques', 'ar': 'الإحصائيات'},
    'total_students': {'fr': 'Total élèves', 'ar': 'مجموع الطلاب'},
    'total_subjects': {'fr': 'Total matières', 'ar': 'مجموع المواد'},
    'class_average': {'fr': 'Moyenne de classe', 'ar': 'معدل الفصل'},
    
    # Observations et commentaires
    'observations': {'fr': 'Observations', 'ar': 'الملاحظات'},
    'general_observations': {'fr': 'Observations générales', 'ar': 'الملاحظات العامة'},
    'comments': {'fr': 'Commentaires', 'ar': 'التعليقات'},
    
    # Signatures
    'signatures': {'fr': 'Signatures', 'ar': 'التوقيعات'},
    'director_signature': {'fr': 'Le Directeur', 'ar': 'المدير'},
    'parents_signature': {'fr': 'Les Parents', 'ar': 'الوالدين'},
    
    # Langue
    'language': {'fr': 'Langue', 'ar': 'اللغة'},
    'french': {'fr': 'Français', 'ar': 'الفرنسية'},
    'arabic': {'fr': 'العربية', 'ar': 'العربية'}
}

def t(key, lang='fr'):
    """Fonction de traduction"""
    return TRANSLATIONS.get(key, {}).get(lang, key)

def get_translation(key, lang='fr'):
    """Alias pour la fonction t()"""
    return t(key, lang)